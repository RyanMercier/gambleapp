<script>
  import { onMount, onDestroy } from 'svelte';
  import Chart from 'chart.js/auto';
  import apiFetch from '$lib/api';

  export let targetId;
  export let targetName = '';
  export let height = '400px';
  export let showTimeframeSelector = true;
  export let autoUpdate = true;
  export let showPositionInfo = true; // FIX 5: Show position info with real-time updates

  let chartCanvas = null;
  let chart = null;
  let loading = true;
  let error = null;
  let selectedTimeframe = '7';
  let chartData = null;
  let websocket = null;
  let lastUpdate = null;
  let isConnected = false;
  let updateInterval = null;
  
  // FIX 5: Position tracking
  let userPosition = null;
  let positionPnL = 0;
  let positionValue = 0;

  const UPDATE_INTERVAL = 15000; // 15 seconds for position updates
  const CHART_UPDATE_INTERVAL = 60000; // 1 minute for chart data

  const timeframes = [
    { value: '1', label: '1D', description: '1 Day' },
    { value: '7', label: '1W', description: '1 Week' },
    { value: '30', label: '1M', description: '1 Month' },
    { value: '90', label: '3M', description: '3 Months' },
    { value: '180', label: '6M', description: '6 Months' },
    { value: '365', label: '1Y', description: '1 Year' },
    { value: '1825', label: '5Y', description: '5 Years' }
  ];

  onMount(async () => {
    console.log('AttentionChart mounted with targetId:', targetId);
    
    if (targetId) {
      await Promise.all([
        loadChart(),
        loadUserPosition() // FIX 5: Load user position data
      ]);
      
      if (autoUpdate) {
        setupRealTimeUpdates(); // FIX 5: Enhanced real-time updates
      }
    } else {
      console.error('AttentionChart: No targetId provided');
      error = 'No target ID provided';
      loading = false;
    }
  });

  onDestroy(() => {
    destroyChart();
    if (websocket) {
      websocket.close();
    }
    if (updateInterval) {
      clearInterval(updateInterval);
    }
  });

  // FIX 5: Load user's position in this target
  async function loadUserPosition() {
    if (!showPositionInfo) return;
    
    try {
      const portfolioData = await apiFetch('/portfolio');
      
      // Find position for this target
      const position = portfolioData.positions?.find(p => p.target_id == targetId);
      
      if (position) {
        userPosition = position;
        positionValue = position.current_value;
        positionPnL = position.unrealized_pnl;
        console.log(`📊 User position in ${targetName}:`, position);
      } else {
        userPosition = null;
        positionValue = 0;
        positionPnL = 0;
      }
    } catch (err) {
      console.error('Failed to load user position:', err);
      // Don't show error for position loading failure
    }
  }

  // FIX 5: Enhanced real-time updates
  function setupRealTimeUpdates() {
    if (updateInterval) clearInterval(updateInterval);
    
    // Update position info more frequently
    updateInterval = setInterval(async () => {
      await loadUserPosition();
      
      // Update chart data less frequently to avoid API spam
      if (lastUpdate && (Date.now() - lastUpdate.getTime()) > CHART_UPDATE_INTERVAL) {
        await loadChart();
      }
    }, UPDATE_INTERVAL);

    // Try WebSocket connection for real-time price updates
    connectWebSocket();
  }

  function connectWebSocket() {
    if (!targetId || websocket?.readyState === WebSocket.OPEN) return;

    try {
      const wsUrl = `ws://localhost:8000/ws/attention/${targetId}`;
      websocket = new WebSocket(wsUrl);
      
      websocket.onopen = () => {
        console.log(`📡 WebSocket connected for target ${targetId}`);
        isConnected = true;
      };
      
      websocket.onmessage = (event) => {
        handleRealTimeUpdate(JSON.parse(event.data));
      };
      
      websocket.onclose = () => {
        console.log('📡 WebSocket disconnected');
        isConnected = false;
        // Reconnect after 5 seconds
        setTimeout(() => {
          if (autoUpdate) connectWebSocket();
        }, 5000);
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        isConnected = false;
      };
    } catch (err) {
      console.error('WebSocket connection failed:', err);
      isConnected = false;
    }
  }

  function handleRealTimeUpdate(data) {
    if (data.target_id != targetId) return;
    
    console.log(`📈 Real-time update: ${data.attention_score}%`);
    
    lastUpdate = new Date(data.timestamp);
    
    // FIX 5: Update position value in real-time when score changes
    if (userPosition && data.attention_score) {
      updatePositionValue(data.attention_score);
    }
    
    // Update chart if it exists
    if (chart && chartData) {
      const newDataPoint = {
        timestamp: data.timestamp,
        attention_score: data.attention_score,
        data_source: 'real_time'
      };
      
      chartData.data.push(newDataPoint);
      
      // Keep only recent data points for the selected timeframe
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - parseInt(selectedTimeframe));
      
      chartData.data = chartData.data.filter(point => 
        new Date(point.timestamp) >= cutoffDate
      );
      
      updateChartData();
      updateSummaryStats();
      
      if (chart) {
        chart.update('none');
      }
    }
  }

  // FIX 5: Calculate real-time position value updates
  function updatePositionValue(newAttentionScore) {
    if (!userPosition) return;
    
    const currentScore = parseFloat(newAttentionScore);
    const entryScore = userPosition.average_entry_score;
    const stakes = userPosition.attention_stakes;
    const positionType = userPosition.position_type;
    
    if (entryScore && stakes) {
      const scoreRatio = currentScore / entryScore;
      
      if (positionType === "long") {
        positionValue = stakes * scoreRatio;
        positionPnL = positionValue - stakes;
      } else if (positionType === "short") {
        positionValue = stakes * (2.0 - scoreRatio);
        positionPnL = positionValue - stakes;
      }
    }
  }

  // Reactive statement to render chart when both canvas and data are ready
  $: if (chartCanvas && chartData && chartData.data && chartData.data.length > 0) {
    console.log('📊 Reactive render: Canvas and data both ready');
    renderChart(chartData);
  }

  $: if (targetId && targetId !== chartData?.target?.id) {
    console.log('📊 Target ID changed, reloading chart');
    loadChart();
    loadUserPosition(); // FIX 5: Reload position when target changes
  }

  async function loadChart() {
    if (!targetId) {
      console.error('loadChart: No targetId provided');
      error = 'No target ID provided for chart';
      loading = false;
      return;
    }

    loading = true;
    error = null;
    console.log(`Loading chart for targetId: ${targetId}, timeframe: ${selectedTimeframe} days`);

    try {
      chartData = await apiFetch(`/targets/${targetId}/chart?days=${selectedTimeframe}`);
      
      console.log('Chart data received:', chartData);
      console.log(`📊 Sampling info:`, chartData?.sampling_info);
      
      if (!chartData || !chartData.data || chartData.data.length === 0) {
        throw new Error('No chart data available');
      }
      
      console.log(`✅ Loaded ${chartData.data.length} data points for ${chartData.target?.name} (${chartData.sampling_info?.granularity})`);
      
      renderChart(chartData);
    } catch (err) {
      error = err.message;
      console.error('Chart loading error for targetId', targetId, ':', err);
    } finally {
      loading = false;
    }
  }

  async function changeTimeframe(newTimeframe) {
    if (selectedTimeframe === newTimeframe) return;
    
    console.log(`Changing timeframe from ${selectedTimeframe} to ${newTimeframe} days`);
    selectedTimeframe = newTimeframe;
    
    await loadChart();
  }

  function renderChart(data) {
    destroyChart();

    if (!chartCanvas) {
      console.error('Cannot render chart: canvas element not available');
      return;
    }

    if (!data || !data.data || data.data.length === 0) {
      console.error('Cannot render chart: no data available', data);
      return;
    }

    console.log(`📊 Rendering chart with ${data.data.length} intelligently sampled data points`);
    console.log(`🎯 Granularity: ${data.sampling_info?.granularity}, Total available: ${data.sampling_info?.total_points_available}`);

    const ctx = chartCanvas.getContext('2d');
    
    const labels = data.data.map(point => {
      const date = new Date(point.timestamp);
      const samplingInfo = data.sampling_info;
      
      if (samplingInfo?.granularity?.includes('minutes') || selectedTimeframe <= 1) {
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          hour: '2-digit',
          minute: '2-digit'
        });
      } else if (samplingInfo?.granularity?.includes('hour') || selectedTimeframe <= 7) {
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          hour: '2-digit' 
        });
      } else if (selectedTimeframe <= 365) {
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric' 
        });
      } else {
        return date.toLocaleDateString('en-US', { 
          year: 'numeric', 
          month: 'short' 
        });
      }
    });

    const attentionData = data.data.map(point => parseFloat(point.attention_score));

    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.05)');

    const pointRadius = data.data.length <= 50 ? 4 : data.data.length <= 100 ? 3 : 2;

    chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: `${data.target?.name || targetName} Attention Score`,
          data: attentionData,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: gradient,
          borderWidth: 2,
          fill: true,
          tension: 0.1,
          pointRadius: pointRadius,
          pointHoverRadius: pointRadius + 2,
          pointBackgroundColor: 'rgb(59, 130, 246)',
          pointBorderColor: 'white',
          pointBorderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgb(59, 130, 246)',
            borderWidth: 1,
            callbacks: {
              title: function(context) {
                return labels[context[0].dataIndex];
              },
              label: function(context) {
                return `Attention: ${context.parsed.y.toFixed(1)}%`;
              }
            }
          }
        },
        scales: {
          x: {
            display: true,
            grid: {
              display: false
            },
            ticks: {
              color: 'rgba(156, 163, 175, 0.7)',
              maxTicksLimit: 8
            }
          },
          y: {
            display: true,
            grid: {
              color: 'rgba(75, 85, 99, 0.2)'
            },
            ticks: {
              color: 'rgba(156, 163, 175, 0.7)',
              callback: function(value) {
                return value.toFixed(0) + '%';
              }
            },
            beginAtZero: false
          }
        },
        interaction: {
          intersect: false,
          mode: 'index'
        }
      }
    });

    updateSummaryStats();
  }

  function updateChartData() {
    if (!chart || !chartData) return;
    
    const labels = chartData.data.map(point => {
      const date = new Date(point.timestamp);
      const samplingInfo = chartData.sampling_info;
      
      if (samplingInfo?.granularity?.includes('minutes') || selectedTimeframe <= 1) {
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          hour: '2-digit',
          minute: '2-digit'
        });
      } else if (samplingInfo?.granularity?.includes('hour') || selectedTimeframe <= 7) {
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          hour: '2-digit' 
        });
      } else if (selectedTimeframe <= 365) {
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric' 
        });
      } else {
        return date.toLocaleDateString('en-US', { 
          year: 'numeric', 
          month: 'short' 
        });
      }
    });
    
    const attentionData = chartData.data.map(point => parseFloat(point.attention_score));
    
    chart.data.labels = labels;
    chart.data.datasets[0].data = attentionData;
    chart.update('none');
  }

  function updateSummaryStats() {
    if (!chartData || !chartData.data.length) return;
    
    const scores = chartData.data.map(point => parseFloat(point.attention_score));
    chartData.summary = {
      average: Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100) / 100,
      max: Math.max(...scores),
      min: Math.min(...scores),
      latest: scores[scores.length - 1],
      change_percent: scores.length > 1 ? 
        Math.round(((scores[scores.length - 1] - scores[0]) / scores[0] * 100) * 100) / 100 : 0,
      data_points: chartData.sampling_info?.total_points_available || scores.length,
      sampled_points: scores.length
    };
  }

  function destroyChart() {
    if (chart) {
      chart.destroy();
      chart = null;
    }
  }

  function formatCurrency(value) {
    if (!value && value !== 0) return '$0.00';
    const abs = Math.abs(value);
    const sign = value >= 0 ? '+' : '-';
    return value >= 0 ? `$${abs.toFixed(2)}` : `-$${abs.toFixed(2)}`;
  }

  function getPnLColorClass(value) {
    if (!value && value !== 0) return 'text-gray-400';
    return value >= 0 ? 'text-emerald-400' : 'text-red-400';
  }
</script>

<div class="attention-chart-container">
  <!-- Chart Header with Position Info -->
  {#if showPositionInfo}
    <div class="mb-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <h3 class="text-lg font-semibold text-white">
            {targetName || chartData?.target?.name || 'Loading...'}
          </h3>
          {#if isConnected}
            <div class="flex items-center gap-2 text-xs text-emerald-400">
              <div class="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
              Live
            </div>
          {/if}
        </div>
        
        <!-- FIX 5: Real-time position display -->
        {#if userPosition}
          <div class="flex items-center gap-6 text-sm">
            <div class="text-center">
              <div class="text-gray-400 text-xs">Position</div>
              <div class="font-semibold text-blue-400">
                {userPosition.position_type.toUpperCase()}
              </div>
            </div>
            <div class="text-center">
              <div class="text-gray-400 text-xs">Stake</div>
              <div class="font-semibold">
                {formatCurrency(userPosition.attention_stakes)}
              </div>
            </div>
            <div class="text-center">
              <div class="text-gray-400 text-xs">Value</div>
              <div class="font-semibold">
                {formatCurrency(positionValue)}
              </div>
            </div>
            <div class="text-center">
              <div class="text-gray-400 text-xs">P&L</div>
              <div class="font-semibold {getPnLColorClass(positionPnL)}">
                {formatCurrency(positionPnL)}
              </div>
            </div>
          </div>
        {:else}
          <div class="text-sm text-gray-400">
            No position
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Chart Content -->
  <div class="chart-content" style="height: {height};">
    {#if loading}
      <div class="flex items-center justify-center h-full">
        <div class="text-center">
          <div class="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
          <p class="text-gray-400">Loading attention data...</p>
        </div>
      </div>
    {:else if error}
      <div class="flex items-center justify-center h-full">
        <div class="text-center">
          <div class="text-red-400 mb-2">⚠️ Error</div>
          <p class="text-gray-400 text-sm">{error}</p>
          <button class="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm" on:click={loadChart}>
            Retry
          </button>
        </div>
      </div>
    {:else}
      <div class="chart-wrapper h-full">
        <canvas bind:this={chartCanvas} class="w-full h-full"></canvas>
      </div>
    {/if}
  </div>

  <!-- Timeframe Selector -->
  {#if showTimeframeSelector && !loading && !error}
    <div class="flex justify-center mt-4 gap-1">
      {#each timeframes as timeframe}
        <button
          class="px-3 py-1 text-xs rounded-md border transition-all duration-200 {
            selectedTimeframe === timeframe.value 
              ? 'bg-blue-600 border-blue-600 text-white' 
              : 'border-gray-600 text-gray-300 hover:border-gray-500 hover:bg-gray-800'
          }"
          on:click={() => changeTimeframe(timeframe.value)}
          title={timeframe.description}
        >
          {timeframe.label}
        </button>
      {/each}
    </div>
  {/if}

  <!-- Chart Summary Stats -->
  {#if chartData?.summary && !loading}
    <div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
      <div class="text-center p-2 bg-gray-800/30 rounded">
        <div class="text-gray-400">Current</div>
        <div class="font-semibold text-blue-400">{chartData.summary.latest.toFixed(1)}%</div>
      </div>
      <div class="text-center p-2 bg-gray-800/30 rounded">
        <div class="text-gray-400">Change</div>
        <div class="font-semibold {chartData.summary.change_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}">
          {chartData.summary.change_percent >= 0 ? '+' : ''}{chartData.summary.change_percent.toFixed(1)}%
        </div>
      </div>
      <div class="text-center p-2 bg-gray-800/30 rounded">
        <div class="text-gray-400">High</div>
        <div class="font-semibold">{chartData.summary.max.toFixed(1)}%</div>
      </div>
      <div class="text-center p-2 bg-gray-800/30 rounded">
        <div class="text-gray-400">Low</div>
        <div class="font-semibold">{chartData.summary.min.toFixed(1)}%</div>
      </div>
    </div>
  {/if}
</div>

<style>
  .attention-chart-container {
    width: 100%;
  }

  .chart-content {
    position: relative;
  }

  .chart-wrapper {
    position: relative;
  }

  canvas {
    display: block;
  }

  /* Real-time update animation */
  .animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: .5;
    }
  }
</style>