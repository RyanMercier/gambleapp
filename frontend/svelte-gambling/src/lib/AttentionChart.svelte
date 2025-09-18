<script>
  import { onMount, onDestroy } from 'svelte';
  import Chart from 'chart.js/auto';
  import apiFetch from '$lib/api'; // FIX: Import the API utility

  export let targetId;
  export let targetName = '';
  export let height = '400px';
  export let showTimeframeSelector = true;
  export let autoUpdate = true; // Enable real-time updates
  export let showPositions = true; // Show position entry points

  let chartCanvas = null;
  let chart = null;
  let loading = true;
  let error = null;
  let selectedTimeframe = '7';
  let chartData = null;
  let websocket = null;
  let lastUpdate = null;
  let isConnected = false;
  let userTrades = [];
  let userPositions = [];

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
    console.log('AttentionChart mounted with targetId:', targetId); // Debug log
    if (targetId) {
      await loadChart();
      if (autoUpdate) {
        connectWebSocket();
      }
    } else {
      console.error('AttentionChart: No targetId provided');
      error = 'No target ID provided';
      loading = false;
    }
  });

  // Reactive statement to render chart when both canvas and data are ready
  $: if (chartCanvas && chartData && chartData.data && chartData.data.length > 0) {
    console.log('📊 Reactive render: Canvas and data both ready');
    renderChart(chartData);
  }

  $: if (targetId) {
    console.log('Target ID changed to:', targetId);
    loadChart();
  }

  onDestroy(() => {
    destroyChart();
    disconnectWebSocket();
  });

  async function connectWebSocket() {
    if (!targetId || websocket) return;
    
    try {
      // Use environment variable for WebSocket URL
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8091';
      const wsUrl = apiBaseUrl.replace('http', 'ws') + `/ws/${targetId}`;
      websocket = new WebSocket(wsUrl);
      
      websocket.onopen = () => {
        isConnected = true;
        console.log(`✅ WebSocket connected for target ${targetId}`);
      };
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleRealtimeUpdate(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      websocket.onclose = () => {
        isConnected = false;
        console.log(`🔌 WebSocket disconnected for target ${targetId}`);
        
        // Attempt to reconnect after 5 seconds
        if (autoUpdate) {
          setTimeout(() => {
            connectWebSocket();
          }, 5000);
        }
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        isConnected = false;
      };
      
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }

  function disconnectWebSocket() {
    if (websocket) {
      websocket.close();
      websocket = null;
      isConnected = false;
    }
  }

  function handleRealtimeUpdate(data) {
    if (data.type === 'attention_update' || data.type === 'forced_update') {
      console.log(`📈 Real-time update: ${data.attention_score}%`);
      
      lastUpdate = new Date(data.timestamp);
      
      // Add new data point to chart if it exists
      if (chart && chartData) {
        const newDataPoint = {
          timestamp: data.timestamp,
          attention_score: data.attention_score,
          data_source: 'google_trends_api'
        };
        
        // Add to chart data
        chartData.data.push(newDataPoint);
        
        // Keep only recent data points for the selected timeframe
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - parseInt(selectedTimeframe));
        
        chartData.data = chartData.data.filter(point => 
          new Date(point.timestamp) >= cutoffDate
        );
        
        // Update the chart
        updateChartData();
        
        // Update summary statistics
        updateSummaryStats();

        // FIX: Force chart refresh - add this line to ensure the chart actually updates
        if (chart) {
          chart.update('none'); // Force immediate chart update without animation
        }
      }
    }
  }

  function updateChartData() {
    if (!chart || !chartData) return;
    
    // No more client-side filtering - just display the data from backend
    const labels = chartData.data.map(point => {
      const date = new Date(point.timestamp);
      
      // Adjust label format based on sampling granularity - Display in user's local timezone
      const samplingInfo = chartData.sampling_info;

      if (samplingInfo?.granularity?.includes('minutes') || selectedTimeframe <= 1) {
        // For minute/hourly data, show time in user's timezone
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
      } else if (samplingInfo?.granularity?.includes('hour') || selectedTimeframe <= 7) {
        // For hourly data, show date + hour in user's timezone
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit'
        });
      } else if (selectedTimeframe <= 365) {
        // For daily/weekly data, show date only in user's timezone
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric'
        });
      } else {
        // For monthly/yearly data, show month/year in user's timezone
        return date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short'
        });
      }
    });
    
    const attentionData = chartData.data.map(point => parseFloat(point.attention_score));
    
    chart.data.labels = labels;
    chart.data.datasets[0].data = attentionData;
    chart.update('none'); // Update without animation for real-time feel
  }

  function updateSummaryStats() {
    if (!chartData || !chartData.data.length) return;
    
    // Calculate stats from the sampled data (which is representative)
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
      // Load chart data and user positions in parallel
      const promises = [
        apiFetch(`/targets/${targetId}/chart?days=${selectedTimeframe}`)
      ];

      if (showPositions) {
        promises.push(loadUserTrades());
      }

      const [chartDataResponse] = await Promise.all(promises);
      chartData = chartDataResponse;

      console.log('Chart data received:', chartData);
      console.log(`📊 Sampling info:`, chartData?.sampling_info);

      // Verify we have data
      if (!chartData || !chartData.data || chartData.data.length === 0) {
        throw new Error('No chart data available');
      }

      console.log(`✅ Loaded ${chartData.data.length} data points for ${chartData.target?.name} (${chartData.sampling_info?.granularity})`);

      // Render chart immediately - canvas should be available
      renderChart(chartData);
    } catch (err) {
      error = err.message;
      console.error('Chart loading error for targetId', targetId, ':', err);
    } finally {
      loading = false;
    }
  }

  async function loadUserTrades() {
    try {
      const trades = await apiFetch('/trades/my');
      // Filter trades for this specific target
      userTrades = trades.trades.filter(trade => trade.target_id === targetId);

      // Also get current portfolio positions for this target
      const portfolio = await apiFetch('/portfolio');
      userPositions = portfolio.positions.filter(position => position.target_id === targetId);

      console.log(`📈 Loaded ${userTrades.length} trades and ${userPositions.length} positions for target ${targetId}`);
    } catch (err) {
      console.error('Failed to load user trades:', err);
      userTrades = [];
      userPositions = [];
    }
  }

  async function changeTimeframe(newTimeframe) {
    if (selectedTimeframe === newTimeframe) return;
    
    console.log(`Changing timeframe from ${selectedTimeframe} to ${newTimeframe} days`);
    selectedTimeframe = newTimeframe;
    
    // Simply reload chart with new timeframe - backend handles the rest
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
        
        // Dynamic label formatting based on granularity - Display in user's local timezone
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

      // Adjust point size based on number of points
      const pointRadius = data.data.length <= 50 ? 4 : data.data.length <= 100 ? 3 : 2;

      // Prepare datasets
      const datasets = [
        {
          label: 'Google Trends Score',
          data: attentionData,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: gradient,
          borderWidth: 2,
          tension: 0.4,
          pointRadius: pointRadius,
          pointHoverRadius: pointRadius + 2,
          pointBackgroundColor: 'rgb(59, 130, 246)',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          fill: true,
          yAxisID: 'y'
        }
      ];

      // Add position entry points if showPositions is enabled and we have trades
      if (showPositions && userTrades.length > 0) {
        const positionEntries = getPositionEntryPoints(data.data, labels);
        if (positionEntries.length > 0) {
          datasets.push({
            label: 'Long Entries',
            data: positionEntries.filter(p => p.type === 'long').map(p => ({ x: p.label, y: p.score })),
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgb(34, 197, 94)',
            borderWidth: 0,
            pointRadius: 8,
            pointHoverRadius: 10,
            pointStyle: 'triangle',
            showLine: false,
            yAxisID: 'y'
          });

          datasets.push({
            label: 'Short Entries',
            data: positionEntries.filter(p => p.type === 'short').map(p => ({ x: p.label, y: p.score })),
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgb(239, 68, 68)',
            borderWidth: 0,
            pointRadius: 8,
            pointHoverRadius: 10,
            pointStyle: 'rectRot',
            showLine: false,
            yAxisID: 'y'
          });
        }
      }

      chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            title: {
              display: true,
              text: `${data.target.name} - Attention Trends (${data.sampling_info?.granularity || 'optimized sampling'})`,
              color: '#F8FAFC',
              font: {
                size: 16,
                weight: 'bold'
              }
            },
            legend: {
              display: showPositions && userTrades.length > 0,
              position: 'top',
              labels: {
                color: '#CBD5E1',
                usePointStyle: true,
                pointStyle: 'circle',
                font: {
                  size: 12
                }
              }
            },
            tooltip: {
              backgroundColor: 'rgba(17, 24, 39, 0.9)',
              titleColor: '#F8FAFC',
              bodyColor: '#CBD5E1',
              borderColor: '#374151',
              borderWidth: 1,
              callbacks: {
                afterBody: function(context) {
                  const datasetIndex = context[0].datasetIndex;
                  const pointIndex = context[0].dataIndex;

                  // Check if this is a position entry point
                  if (datasetIndex > 0 && showPositions) {
                    const positionEntries = getPositionEntryPoints(chartData.data, chart.data.labels);
                    const entryType = datasetIndex === 1 ? 'long' : 'short';
                    const entry = positionEntries.filter(p => p.type === entryType)[pointIndex];

                    if (entry && entry.trade) {
                      return [
                        `Position: ${entry.type.toUpperCase()}`,
                        `Entry Score: ${entry.score}%`,
                        `Amount: $${entry.trade.stake_amount}`,
                        `Date: ${new Date(entry.trade.timestamp).toLocaleString('en-US')}`
                      ];
                    }
                  }
                  return [];
                }
              }
            }
          },
          scales: {
            x: {
              ticks: {
                color: '#CBD5E1',
                maxTicksLimit: Math.min(12, Math.max(6, Math.floor(data.data.length / 5)))
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
                text: 'Google Trends Score (0-100)',
                color: '#CBD5E1'
              },
              ticks: {
                color: '#CBD5E1'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              },
              min: 0,
              max: 100
            }
          }
        }
      });

      // Update summary stats after rendering
      updateSummaryStats();
      console.log('✅ Chart rendered successfully with intelligent sampling');
  }

  function destroyChart() {
    if (chart) {
      chart.destroy();
      chart = null;
    }
  }

  function getSelectedTimeframeName() {
    const timeframe = timeframes.find(t => t.value === selectedTimeframe);
    return timeframe ? timeframe.description : 'Unknown';
  }

  function formatTime(date) {
    return date?.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  function getPositionEntryPoints(chartData, labels) {
    if (!userTrades || userTrades.length === 0) return [];

    const positionEntries = [];

    userTrades.forEach(trade => {
      // Only show entry trades (buy/sell), not close trades
      if (trade.trade_type === 'buy' || trade.trade_type === 'sell') {
        const tradeTime = new Date(trade.timestamp);

        // Find the closest data point in the chart to this trade time
        let closestIndex = -1;
        let closestTimeDiff = Infinity;

        chartData.forEach((point, index) => {
          const pointTime = new Date(point.timestamp);
          const timeDiff = Math.abs(tradeTime.getTime() - pointTime.getTime());

          if (timeDiff < closestTimeDiff) {
            closestTimeDiff = timeDiff;
            closestIndex = index;
          }
        });

        // If we found a close enough point (within the chart timeframe)
        if (closestIndex !== -1 && closestTimeDiff < 24 * 60 * 60 * 1000) { // Within 24 hours
          positionEntries.push({
            type: trade.trade_type === 'buy' ? 'long' : 'short',
            label: labels[closestIndex],
            score: parseFloat(trade.attention_score_at_entry),
            trade: trade
          });
        }
      }
    });

    return positionEntries;
  }
</script>

<div class="attention-chart-container">
  <!-- Header with Real-time Status -->
  {#if showTimeframeSelector}
    <div class="mb-4">
      <div class="flex items-center justify-between mb-3">
        <div>
          <div class="flex items-center gap-3">
            <h3 class="text-lg font-semibold text-white">
              {targetName || (chartData?.target?.name ? `${chartData.target.name}` : 'Google Trends Chart')}
            </h3>
            
            <!-- Real-time status indicator -->
            {#if autoUpdate}
              <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full {isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}"></div>
                <span class="text-xs text-gray-400">
                  {isConnected ? 'Live' : 'Offline'}
                </span>
              </div>
            {/if}
          </div>
          
          {#if chartData?.summary}
            <div class="flex items-center gap-4 mt-1 text-sm text-gray-400">
              <span>Latest: {chartData.summary.latest.toFixed(1)}%</span>
              <span class="flex items-center gap-1">
                Change: 
                <span class="{chartData.summary.change_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                  {chartData.summary.change_percent >= 0 ? '+' : ''}{chartData.summary.change_percent.toFixed(1)}%
                </span>
              </span>
              <span>Avg: {chartData.summary.average.toFixed(1)}%</span>
              {#if lastUpdate}
                <span class="text-xs">Updated: {formatTime(lastUpdate)}</span>
              {/if}
            </div>
          {/if}
        </div>
        
        <!-- Controls -->
        <div class="flex items-center gap-3">
          <!-- Position Toggle -->
          {#if showPositions}
            <button
              class="px-3 py-2 text-sm rounded-md transition-all duration-200 font-medium {
                userTrades.length > 0
                  ? 'bg-green-600 text-white shadow-md'
                  : 'bg-gray-600 text-gray-400'
              }"
              on:click={() => { showPositions = !showPositions; loadChart(); }}
              disabled={loading}
              title="Toggle position entry points"
            >
              📈 Positions ({userTrades.length})
            </button>
          {/if}

          <!-- Timeframe Selector -->
          <div class="flex bg-gray-800 rounded-lg p-1 shadow-inner">
            {#each timeframes as timeframe}
              <button
                class="px-3 py-2 text-sm rounded-md transition-all duration-200 font-medium {
                  selectedTimeframe === timeframe.value
                    ? 'bg-blue-600 text-white shadow-md transform scale-[1.02]'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }"
                on:click={() => changeTimeframe(timeframe.value)}
                disabled={loading}
                title={timeframe.description}
              >
                {timeframe.label}
              </button>
            {/each}
          </div>
        </div>
      </div>
      
      <!-- Data Source Info -->
      <div class="flex items-center justify-between text-xs text-gray-500">
        <div>
          Showing {getSelectedTimeframeName()} of Google Trends data
          {#if chartData?.sampling_info}
            <span class="ml-2 px-2 py-1 bg-gray-800 rounded text-gray-300">
              {chartData.sampling_info.points_returned} points
              {#if chartData.sampling_info.total_points_available > chartData.sampling_info.points_returned}
                (sampled from {chartData.sampling_info.total_points_available})
              {/if}
              • {chartData.sampling_info.granularity}
            </span>
          {:else if chartData?.data?.length}
            ({chartData.data.length} data points)
          {/if}
        </div>
        
        <div class="flex items-center gap-1">
          <svg class="w-3 h-3 text-green-400" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
          </svg>
          <span>Intelligently Sampled Data</span>
        </div>
      </div>
    </div>
  {/if}

  <!-- Chart Container -->
  <div class="relative bg-gray-900 rounded-lg p-4 shadow-lg border border-gray-800" style="height: {height}">
    <!-- Always render canvas -->
    <canvas bind:this={chartCanvas} class="w-full h-full"></canvas>
    
    <!-- Loading overlay -->
    {#if loading}
      <div class="absolute inset-0 flex items-center justify-center bg-gray-900/90">
        <div class="flex flex-col items-center gap-3">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span class="text-gray-400 text-sm">Loading chart for target {targetId}...</span>
        </div>
      </div>
    {/if}
    
    <!-- Error overlay -->
    {#if error}
      <div class="absolute inset-0 flex items-center justify-center bg-gray-900/90">
        <div class="text-center">
          <div class="text-red-400 mb-2">
            <svg class="w-8 h-8 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
            </svg>
          </div>
          <div class="text-red-400 font-medium">{error}</div>
          <div class="text-gray-400 text-sm mt-1">Target ID: {targetId}</div>
          <button 
            class="mt-2 text-blue-400 hover:text-blue-300 text-sm underline"
            on:click={loadChart}
          >
            Retry
          </button>
        </div>
      </div>
    {/if}
    
    <!-- No data overlay -->
    {#if !loading && !error && (!chartData?.data?.length)}
      <div class="absolute inset-0 flex items-center justify-center bg-gray-900/90">
        <div class="text-center text-gray-400">
          <div class="text-4xl mb-2">📊</div>
          <div>No Google Trends data available</div>
          <div class="text-sm mt-1">Data is being collected for target {targetId}...</div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .attention-chart-container {
    width: 100%;
  }
  
  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
</style>