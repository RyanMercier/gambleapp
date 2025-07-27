<script>
  import { onMount, onDestroy } from 'svelte';
  import Chart from 'chart.js/auto';

  export let targetId;
  export let targetName = '';
  export let days = 7;
  export let height = '300px';

  let chartCanvas = null;
  let chart = null;
  let loading = true;
  let error = null;

  onMount(async () => {
    if (targetId) {
      await loadChart();
    }
  });

  onDestroy(() => {
    destroyChart();
  });

  async function loadChart() {
    loading = true;
    error = null;

    try {
      const response = await fetch(`/api/targets/${targetId}/chart?days=${days}`);
      if (!response.ok) throw new Error('Failed to load chart data');
      
      const chartData = await response.json();
      renderChart(chartData);
    } catch (err) {
      error = err.message;
      console.error('Chart loading error:', err);
    } finally {
      loading = false;
    }
  }

  function renderChart(data) {
    destroyChart();

    if (!chartCanvas || !data.data.length) return;

    const ctx = chartCanvas.getContext('2d');
    
    const labels = data.data.map(point => {
      const date = new Date(point.timestamp);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    const attentionData = data.data.map(point => parseFloat(point.attention_score));
    const priceData = data.data.map(point => parseFloat(point.share_price));

    chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Attention Score',
            data: attentionData,
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4,
            yAxisID: 'y',
            pointRadius: 3,
            pointHoverRadius: 6
          },
          {
            label: 'Share Price ($)',
            data: priceData,
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.4,
            yAxisID: 'y1',
            pointRadius: 3,
            pointHoverRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          title: {
            display: !!targetName,
            text: `${targetName} - Attention & Price Trends`,
            color: '#F8FAFC',
            font: {
              size: 16,
              weight: 'bold'
            }
          },
          legend: {
            labels: {
              color: '#F8FAFC',
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#F8FAFC',
            bodyColor: '#F8FAFC',
            borderColor: 'rgba(59, 130, 246, 0.5)',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            ticks: {
              color: '#CBD5E1'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Attention Score',
              color: '#CBD5E1'
            },
            ticks: {
              color: '#CBD5E1'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Share Price ($)',
              color: '#CBD5E1'
            },
            ticks: {
              color: '#CBD5E1',
              callback: function(value) {
                return '$' + value.toFixed(2);
              }
            },
            grid: {
              drawOnChartArea: false,
            }
          }
        }
      }
    });
  }

  function destroyChart() {
    if (chart) {
      chart.destroy();
      chart = null;
    }
  }

  // Watch for changes
  $: if (targetId) {
    loadChart();
  }
</script>

<div class="w-full" style="height: {height}">
  {#if loading}
    <div class="flex items-center justify-center h-full bg-gray-800/50 rounded-lg">
      <div class="flex flex-col items-center gap-2">
        <div class="w-6 h-6 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
        <span class="text-sm text-gray-400">Loading chart...</span>
      </div>
    </div>
  {:else if error}
    <div class="flex items-center justify-center h-full bg-red-500/10 border border-red-500/20 rounded-lg">
      <div class="text-center">
        <div class="text-red-400 text-sm mb-2">⚠️ Chart Error</div>
        <div class="text-gray-400 text-xs">{error}</div>
        <button 
          class="btn btn-secondary text-xs mt-2"
          on:click={loadChart}
        >
          Retry
        </button>
      </div>
    </div>
  {:else}
    <div class="h-full bg-gray-800/50 rounded-lg p-4">
      <canvas bind:this={chartCanvas} class="w-full h-full"></canvas>
    </div>
  {/if}
</div>