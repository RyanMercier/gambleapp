<script>
  import { onMount, onDestroy } from 'svelte';
  import apiFetch from '$lib/api';

  export let showDetailed = false;
  
  let portfolioData = null;
  let loading = true;
  let error = null;
  let updateInterval = null;
  
  // FIX 5: Real-time updates every 30 seconds
  const UPDATE_INTERVAL = 30000; // 30 seconds

  onMount(async () => {
    await loadPnLData();
    
    // Set up real-time updates
    if (updateInterval) clearInterval(updateInterval);
    updateInterval = setInterval(() => {
      loadPnLData();
    }, UPDATE_INTERVAL);
  });

  onDestroy(() => {
    if (updateInterval) {
      clearInterval(updateInterval);
    }
  });

  async function loadPnLData() {
    try {
      // FIX 2: Use corrected portfolio endpoint that calculates P&L properly
      const data = await apiFetch('/portfolio');
      portfolioData = data;
      error = null;
    } catch (err) {
      console.error('Failed to load P&L data:', err);
      error = 'Failed to load P&L';
    } finally {
      loading = false;
    }
  }

  function formatPnL(value) {
    if (!value && value !== 0) return '$0.00';
    const formatted = Math.abs(value).toFixed(2);
    const sign = value >= 0 ? '+' : '-';
    return `${sign}$${formatted}`;
  }

  function getPnLColorClass(value) {
    if (!value && value !== 0) return 'text-gray-400';
    return value >= 0 ? 'text-emerald-400' : 'text-red-400';
  }

  // FIX 2: Calculate total P&L correctly from all open positions
  $: totalUnrealizedPnL = portfolioData?.total_unrealized_pnl || 0;
  $: totalRealizedPnL = portfolioData?.realized_daily_pnl || 0;
  $: totalDailyPnL = totalUnrealizedPnL + totalRealizedPnL;
</script>

{#if loading}
  <div class="flex items-center gap-2">
    <div class="w-4 h-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
    <span class="text-sm text-gray-400">Loading P&L...</span>
  </div>
{:else if error}
  <div class="text-sm text-red-400">
    {error}
  </div>
{:else if portfolioData}
  <div class="flex items-center gap-4">
    <!-- FIX 2: Show total daily P&L (realized + unrealized) -->
    <div class="flex items-center gap-2">
      <span class="text-sm text-gray-400">Today's P&L:</span>
      <span class="font-semibold {getPnLColorClass(totalDailyPnL)}">
        {formatPnL(totalDailyPnL)}
      </span>
    </div>
    
    {#if showDetailed}
      <!-- Detailed breakdown -->
      <div class="flex items-center gap-4 text-xs">
        <div class="flex items-center gap-1">
          <span class="text-gray-500">Unrealized:</span>
          <span class="{getPnLColorClass(totalUnrealizedPnL)}">
            {formatPnL(totalUnrealizedPnL)}
          </span>
        </div>
        <div class="flex items-center gap-1">
          <span class="text-gray-500">Realized:</span>
          <span class="{getPnLColorClass(totalRealizedPnL)}">
            {formatPnL(totalRealizedPnL)}
          </span>
        </div>
        <div class="flex items-center gap-1">
          <span class="text-gray-500">Positions:</span>
          <span class="text-gray-300">{portfolioData.positions?.length || 0}</span>
        </div>
      </div>
    {/if}
  </div>
{:else}
  <div class="text-sm text-gray-400">No P&L data</div>
{/if}

<style>
  /* Add subtle animation for P&L updates */
  .text-emerald-400, .text-red-400 {
    transition: color 0.3s ease;
  }
</style>