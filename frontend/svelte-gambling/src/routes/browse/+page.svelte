<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';
  import Chart from 'chart.js/auto';

  let searchQuery = '';
  let targetType = 'politician';
  let searchResults = null;
  let loading = false;
  let chart = null;
  let chartCanvas = null;
  let popularTargets = [];
  let selectedTarget = null;

  const targetTypes = [
    { value: 'politician', label: '🏛️ Politicians', icon: '🏛️' },
    { value: 'billionaire', label: '💰 Billionaires', icon: '💰' },
    { value: 'country', label: '🌍 Countries', icon: '🌍' },
    { value: 'stock', label: '📈 Stocks', icon: '📈' }
  ];

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    // Load popular targets
    try {
      const targets = await apiFetch('/targets');
      popularTargets = targets.slice(0, 20); // Top 20 by attention score
    } catch (error) {
      console.error('Failed to load popular targets:', error);
    }
  });

  async function searchTrends() {
    if (!searchQuery.trim()) return;
    
    loading = true;
    destroyChart();

    try {
      const data = await apiFetch('/search', {
        method: 'POST',
        body: JSON.stringify({
          query: searchQuery.trim(),
          target_type: targetType
        })
      });

      searchResults = data;
      await loadTargetChart(data.target_id);
    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed: ' + error.message);
    } finally {
      loading = false;
    }
  }

  async function loadTargetChart(targetId, days = 7) {
    try {
      const chartData = await apiFetch(`/targets/${targetId}/chart?days=${days}`);
      renderChart(chartData);
    } catch (error) {
      console.error('Failed to load chart data:', error);
    }
  }

  function renderChart(data) {
    destroyChart();

    if (!chartCanvas) return;

    const ctx = chartCanvas.getContext('2d');
    
    // Prepare data for Chart.js
    const labels = data.data.map(point => {
      const date = new Date(point.timestamp);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    const attentionData = data.data.map(point => point.attention_score);
    const priceData = data.data.map(point => point.share_price);

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
            yAxisID: 'y'
          },
          {
            label: 'Share Price ($)',
            data: priceData,
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.4,
            yAxisID: 'y1'
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
            display: true,
            text: `${data.target.name} - Attention & Price Trends`,
            color: '#F8FAFC',
            font: {
              size: 16,
              weight: 'bold'
            }
          },
          legend: {
            labels: {
              color: '#F8FAFC'
            }
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
              color: '#CBD5E1'
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

  async function selectPopularTarget(target) {
    selectedTarget = target;
    searchQuery = target.name;
    targetType = target.type;
    
    // Load chart for this target
    await loadTargetChart(target.id);
    
    // Set search results to show trading options
    searchResults = {
      target_id: target.id,
      query: target.name,
      current_attention_score: target.attention_score
    };
  }

  function formatNumber(num) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2
    }).format(num);
  }

  function formatPrice(price) {
    return `$${formatNumber(price)}`;
  }

  function getTypeIcon(type) {
    const typeObj = targetTypes.find(t => t.value === type);
    return typeObj ? typeObj.icon : '📊';
  }
</script>

<svelte:head>
  <title>Browse Trends - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
        Browse Attention Trends
      </h1>
      <p class="text-gray-400">Search any term and see its attention score over time. Trade attention like stocks!</p>
    </div>

    <!-- Search Section -->
    <div class="card mb-8">
      <h2 class="text-xl font-semibold mb-4">🔍 Search Trends</h2>
      
      <form on:submit|preventDefault={searchTrends} class="space-y-4">
        <!-- Target Type Selection -->
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">Category</label>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
            {#each targetTypes as type}
              <button
                type="button"
                class="btn {targetType === type.value ? 'btn-primary' : 'btn-secondary'} text-sm"
                on:click={() => targetType = type.value}
              >
                {type.label}
              </button>
            {/each}
          </div>
        </div>

        <!-- Search Input -->
        <div class="flex gap-2">
          <input
            type="text"
            bind:value={searchQuery}
            placeholder="Search for anyone or anything... (e.g., Elon Musk, Bitcoin, Tesla)"
            class="input flex-1"
            required
          />
          <button
            type="submit"
            class="btn btn-primary px-6"
            disabled={loading}
          >
            {#if loading}
              <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            {:else}
              Search
            {/if}
          </button>
        </div>
      </form>
    </div>

    <!-- Chart Section -->
    {#if searchResults}
      <div class="card mb-8">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h2 class="text-xl font-semibold">{searchResults.query}</h2>
            <p class="text-gray-400">Current Attention Score: {formatNumber(searchResults.current_attention_score)}</p>
          </div>
          <div class="flex gap-2">
            <button class="btn btn-success" on:click={() => goto(`/trade/${searchResults.target_id}?type=buy`)}>
              📈 Buy Shares
            </button>
            <button class="btn btn-danger" on:click={() => goto(`/trade/${searchResults.target_id}?type=sell`)}>
              📉 Sell Shares
            </button>
          </div>
        </div>
        
        <!-- Chart Canvas -->
        <div class="h-96 bg-gray-800/50 rounded-lg p-4">
          <canvas bind:this={chartCanvas} class="w-full h-full"></canvas>
        </div>
      </div>
    {/if}

    <!-- Popular Targets -->
    <div class="card">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold">🔥 Trending Now</h2>
        <p class="text-sm text-gray-400">Top targets by attention score</p>
      </div>
      
      {#if popularTargets.length > 0}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {#each popularTargets as target}
            <button
              class="p-4 bg-white/5 rounded-lg hover:bg-white/10 transition-all text-left group"
              on:click={() => selectPopularTarget(target)}
            >
              <div class="flex items-center gap-3 mb-2">
                <span class="text-2xl">{getTypeIcon(target.type)}</span>
                <div class="flex-1 min-w-0">
                  <h3 class="font-medium truncate group-hover:text-blue-400 transition-colors">
                    {target.name}
                  </h3>
                  <p class="text-xs text-gray-400 capitalize">{target.type}</p>
                </div>
              </div>
              
              <div class="space-y-1">
                <div class="flex justify-between text-sm">
                  <span class="text-gray-400">Attention:</span>
                  <span class="font-medium">{formatNumber(target.attention_score)}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-400">Price:</span>
                  <span class="font-medium text-emerald-400">{formatPrice(target.current_price)}</span>
                </div>
              </div>
            </button>
          {/each}
        </div>
      {:else}
        <div class="text-center py-8 text-gray-400">
          <div class="text-3xl mb-2">📊</div>
          <p>Loading trending targets...</p>
        </div>
      {/if}
    </div>
  </div>
</div>