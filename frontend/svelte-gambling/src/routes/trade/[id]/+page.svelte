<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';
  import AttentionChart from '$lib/AttentionChart.svelte';

  let target = null;
  let loading = false;
  let error = '';
  
  // Trading state
  let selectedTournament = null;
  let tournaments = [];
  let longPosition = null;
  let shortPosition = null;
  let tradeAmount = 0;
  let submitting = false;
  let tradeError = '';

  // Chart state
  let showChart = false;
  let chartTargetId = null;
  let chartTargetName = '';

  $: targetId = $page.params.id;
  $: stakeCost = target ? tradeAmount * (target.current_attention_score || target.attention_score || 50) / 10 : 0;
  $: tournamentBalance = selectedTournament ? (selectedTournament.current_balance || 10000) : 0;
  $: canAffordLong = selectedTournament && stakeCost <= tournamentBalance;
  $: canAffordShort = selectedTournament && stakeCost <= tournamentBalance;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    await loadAllData();
  });

  async function loadAllData() {
    loading = true;
    error = '';
    
    try {
      // Load target, tournaments, and positions in parallel
      const [targetData, tournamentsData, portfolioData] = await Promise.all([
        loadTarget(),
        apiFetch('/tournaments').catch(() => []),
        apiFetch('/portfolio').catch(() => ({ positions: [] }))
      ]);

      target = targetData;
      tournaments = Array.isArray(tournamentsData) ? tournamentsData : [];
      
      // Find positions for this target
      if (portfolioData.positions) {
        longPosition = portfolioData.positions.find(p => 
          p.target_id === parseInt(targetId) && (p.position_type === 'long' || !p.position_type)
        );
        shortPosition = portfolioData.positions.find(p => 
          p.target_id === parseInt(targetId) && p.position_type === 'short'
        );
      }

      // Auto-select first tournament if available
      if (tournaments.length > 0 && !selectedTournament) {
        selectedTournament = tournaments[0];
      }

      // Setup chart exactly like browse page
      if (target) {
        chartTargetId = target.id;
        chartTargetName = target.name;
        showChart = true;
      }

    } catch (err) {
      error = err.message || 'Failed to load data';
      console.error('Trade page error:', err);
    } finally {
      loading = false;
    }
  }

  async function loadTarget() {
    const targets = await apiFetch('/targets');
    const found = targets.find(t => t.id === parseInt(targetId));
    if (!found) {
      throw new Error('Target not found');
    }
    return found;
  }

  async function executeTrade(positionType) {
    if (!target || !selectedTournament || submitting) return;

    tradeError = '';

    // Validation
    if (tradeAmount <= 0) {
      tradeError = 'Please enter a valid amount';
      return;
    }

    const canAfford = positionType === 'long' ? canAffordLong : canAffordShort;
    if (!canAfford) {
      tradeError = `Insufficient tournament balance. Need $${stakeCost.toFixed(2)}, have $${tournamentBalance.toFixed(2)}`;
      return;
    }

    submitting = true;

    try {
      const result = await apiFetch('/trade', {
        method: 'POST',
        body: JSON.stringify({
          target_id: parseInt(targetId),
          trade_type: positionType === 'long' ? 'buy' : 'sell',
          shares: tradeAmount,
          tournament_id: selectedTournament.id
        })
      });

      // Show success
      const positionName = positionType === 'long' ? 'Long' : 'Short';
      alert(`✅ ${positionName} position opened! Staked $${stakeCost.toFixed(2)}`);

      // Reset and reload
      tradeAmount = 0;
      await loadAllData();

    } catch (err) {
      tradeError = err.message || 'Trade failed';
      console.error('Trade execution error:', err);
    } finally {
      submitting = false;
    }
  }

  async function closePosition(positionType) {
    if (!target || submitting) return;

    const position = positionType === 'long' ? longPosition : shortPosition;
    if (!position) return;

    submitting = true;
    tradeError = '';

    try {
      // Close by selling the entire position
      const closeAmount = position.attention_stakes / 10; // Convert to shares
      
      const result = await apiFetch('/trade', {
        method: 'POST',
        body: JSON.stringify({
          target_id: parseInt(targetId),
          trade_type: 'sell',
          shares: closeAmount
        })
      });

      const pnlText = result.pnl ? (result.pnl >= 0 ? `+$${result.pnl.toFixed(2)}` : `-$${Math.abs(result.pnl).toFixed(2)}`) : '';
      alert(`✅ ${positionType.toUpperCase()} position closed! ${pnlText ? `P&L: ${pnlText}` : ''}`);

      await loadAllData();

    } catch (err) {
      tradeError = err.message || 'Failed to close position';
      console.error('Close position error:', err);
    } finally {
      submitting = false;
    }
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount || 0).toFixed(2)}`;
  }

  function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) {
      return '0.00';
    }
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2
    }).format(num);
  }

  function getTypeIcon(type) {
    const icons = {
      politician: '🏛️',
      celebrity: '🌟',
      billionaire: '💰',
      country: '🌍',
      stock: '📈',
      crypto: '₿',
      game: '🎮'
    };
    return icons[type] || '📊';
  }
</script>

<svelte:head>
  <title>{target ? `Trade ${target.name}` : 'Trade'} - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">
    {#if loading}
      <div class="text-center py-12">
        <div class="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-gray-400">Loading trading data...</p>
      </div>
    {:else if error && !target}
      <div class="text-center py-12">
        <div class="text-6xl mb-4">⚠️</div>
        <h2 class="text-2xl font-bold mb-2 text-red-400">Error Loading Target</h2>
        <p class="text-gray-400 mb-4">{error}</p>
        <a href="/browse" class="btn btn-primary">← Back to Browse</a>
      </div>
    {:else if target}
      <!-- Target Header -->
      <div class="flex items-center gap-4 mb-6">
        <button 
          class="btn btn-secondary"
          on:click={() => goto('/browse')}
        >
          ← Back
        </button>
        
        <div class="flex items-center gap-3 flex-1">
          <span class="text-4xl">{getTypeIcon(target.type)}</span>
          <div>
            <h1 class="text-3xl font-bold">{target.name}</h1>
            <div class="flex items-center gap-4 text-gray-400">
              <span class="capitalize">{target.type}</span>
              <span>•</span>
              <span>Score: {formatNumber(target.current_attention_score || target.attention_score || 50)}</span>
              {#if target.last_updated}
                <span>•</span>
                <span class="text-sm">Updated {new Date(target.last_updated).toLocaleTimeString()}</span>
              {/if}
            </div>
          </div>
        </div>
      </div>

      <!-- Main Chart Section (exactly like browse page) -->
      <div class="card mb-8">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h2 class="text-xl font-semibold">{target.name}</h2>
            <p class="text-gray-400">Current Attention Score: {formatNumber(target.current_attention_score || target.attention_score || 50)}</p>
            {#if target.description}
              <p class="text-sm text-gray-500 mt-1">{target.description}</p>
            {/if}
          </div>
        </div>
        
        <!-- Attention Chart Component (exactly like browse page) -->
        {#if showChart && chartTargetId}
          <div class="mt-4">
            <AttentionChart 
              targetId={chartTargetId} 
              targetName={chartTargetName}
              height="400px"
              showTimeframeSelector={true}
              autoUpdate={true}
            />
          </div>
        {:else}
          <div class="h-96 bg-gray-800/50 rounded-lg p-4 flex items-center justify-center">
            <div class="text-center text-gray-400">
              <div class="text-4xl mb-2">📊</div>
              <div>Chart loading...</div>
            </div>
          </div>
        {/if}
      </div>

      <!-- Trading Section -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Tournament Selection -->
        <div class="card">
          <h3 class="text-lg font-semibold mb-3">🏆 Tournament</h3>
          
          {#if tournaments.length > 0}
            <select 
              bind:value={selectedTournament} 
              class="input mb-3"
              disabled={submitting}
            >
              {#each tournaments as tournament}
                <option value={tournament}>
                  {tournament.name} ({tournament.entry_fee > 0 ? `$${tournament.entry_fee}` : 'FREE'})
                </option>
              {/each}
            </select>

            {#if selectedTournament}
              <div class="p-3 bg-white/5 rounded-lg">
                <div class="flex justify-between text-sm mb-1">
                  <span>Virtual Balance:</span>
                  <span class="font-bold text-emerald-400">{formatCurrency(tournamentBalance)}</span>
                </div>
                <div class="flex justify-between text-xs text-gray-400">
                  <span>Entry Fee:</span>
                  <span>{selectedTournament.entry_fee > 0 ? formatCurrency(selectedTournament.entry_fee) : 'FREE'}</span>
                </div>
                <div class="flex justify-between text-xs text-gray-400">
                  <span>Players:</span>
                  <span>{selectedTournament.current_participants || 0}</span>
                </div>
                <div class="flex justify-between text-xs text-gray-400">
                  <span>Ends:</span>
                  <span>{new Date(selectedTournament.end_date).toLocaleDateString()}</span>
                </div>
              </div>
            {/if}
          {:else}
            <div class="text-center py-4 text-gray-400">
              <p class="mb-2">No active tournaments</p>
              <a href="/tournaments" class="btn btn-sm btn-primary">Join Tournament</a>
            </div>
          {/if}
        </div>

        <!-- Current Positions -->
        <div class="card">
          <h3 class="text-lg font-semibold mb-3">📊 Your Positions</h3>
          
          {#if longPosition || shortPosition}
            <div class="space-y-3">
              {#if longPosition}
                <div class="p-3 bg-emerald-500/10 rounded-lg">
                  <div class="flex justify-between items-center mb-2">
                    <span class="font-medium text-emerald-400">📈 Long Position</span>
                    <button 
                      class="btn btn-sm btn-danger"
                      on:click={() => closePosition('long')}
                      disabled={submitting}
                    >
                      Close
                    </button>
                  </div>
                  <div class="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span class="text-gray-400">Stake:</span>
                      <div class="font-medium">{formatCurrency(longPosition.attention_stakes)}</div>
                    </div>
                    <div>
                      <span class="text-gray-400">Entry:</span>
                      <div class="font-medium">{formatNumber(longPosition.average_entry_score)}</div>
                    </div>
                    <div>
                      <span class="text-gray-400">Value:</span>
                      <div class="font-medium">{formatCurrency(longPosition.current_value)}</div>
                    </div>
                    <div>
                      <span class="text-gray-400">P&L:</span>
                      <div class="font-medium {(longPosition.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                        {(longPosition.pnl || 0) >= 0 ? '+' : ''}{formatCurrency(longPosition.pnl || 0)}
                      </div>
                    </div>
                  </div>
                </div>
              {/if}

              {#if shortPosition}
                <div class="p-3 bg-orange-500/10 rounded-lg">
                  <div class="flex justify-between items-center mb-2">
                    <span class="font-medium text-orange-400">📉 Short Position</span>
                    <button 
                      class="btn btn-sm btn-danger"
                      on:click={() => closePosition('short')}
                      disabled={submitting}
                    >
                      Close
                    </button>
                  </div>
                  <div class="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span class="text-gray-400">Stake:</span>
                      <div class="font-medium">{formatCurrency(shortPosition.attention_stakes)}</div>
                    </div>
                    <div>
                      <span class="text-gray-400">Entry:</span>
                      <div class="font-medium">{formatNumber(shortPosition.average_entry_score)}</div>
                    </div>
                    <div>
                      <span class="text-gray-400">Value:</span>
                      <div class="font-medium">{formatCurrency(shortPosition.current_value)}</div>
                    </div>
                    <div>
                      <span class="text-gray-400">P&L:</span>
                      <div class="font-medium {(shortPosition.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                        {(shortPosition.pnl || 0) >= 0 ? '+' : ''}{formatCurrency(shortPosition.pnl || 0)}
                      </div>
                    </div>
                  </div>
                </div>
              {/if}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-3xl mb-2">📊</div>
              <p class="text-sm">No positions in {target.name}</p>
              <p class="text-xs mt-1">Open a position below</p>
            </div>
          {/if}
        </div>

        <!-- Trading Form -->
        <div class="card">
          <h3 class="text-lg font-semibold mb-4">💱 Open Position</h3>
          
          {#if !selectedTournament}
            <div class="text-center py-4 text-gray-400">
              <p>Select a tournament to start trading</p>
            </div>
          {:else}
            <!-- Trade Amount Input -->
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Amount to Stake
              </label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                bind:value={tradeAmount}
                class="input"
                placeholder="0.00"
                disabled={submitting}
              />
            </div>

            <!-- Order Summary -->
            {#if tradeAmount > 0}
              <div class="p-3 bg-white/5 rounded-lg mb-4">
                <div class="flex justify-between text-sm mb-1">
                  <span>Stake Cost:</span>
                  <span class="font-medium text-red-400">-{formatCurrency(stakeCost)}</span>
                </div>
                <div class="flex justify-between text-sm mb-1">
                  <span>Current Score:</span>
                  <span class="font-medium">{formatNumber(target.current_attention_score || target.attention_score || 50)}</span>
                </div>
                <div class="flex justify-between text-xs text-gray-400">
                  <span>Available:</span>
                  <span class="{canAffordLong ? 'text-emerald-400' : 'text-red-400'}">{formatCurrency(tournamentBalance)}</span>
                </div>
              </div>
            {/if}

            <!-- Error Message -->
            {#if tradeError}
              <div class="p-2 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm mb-4">
                {tradeError}
              </div>
            {/if}

            <!-- MAIN TRADING BUTTONS -->
            <div class="grid grid-cols-2 gap-3 mb-4">
              <button
                class="btn btn-success py-3"
                on:click={() => executeTrade('long')}
                disabled={submitting || tradeAmount <= 0 || !canAffordLong}
              >
                {#if submitting}
                  <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                {:else}
                  📈 Long
                {/if}
              </button>
              
              <button
                class="btn btn-danger py-3"
                on:click={() => executeTrade('short')}
                disabled={submitting || tradeAmount <= 0 || !canAffordShort}
              >
                {#if submitting}
                  <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                {:else}
                  📉 Short
                {/if}
              </button>
            </div>

            <!-- Flatten All Button -->
            {#if (longPosition && longPosition.attention_stakes > 0) || (shortPosition && shortPosition.attention_stakes > 0)}
              <button
                class="btn btn-warning w-full mb-4"
                on:click={() => {
                  if (longPosition) closePosition('long');
                  if (shortPosition) closePosition('short');
                }}
                disabled={submitting}
              >
                🔄 Flatten All Positions
              </button>
            {/if}

            <!-- Quick Amount Buttons -->
            <div class="mb-4">
              <p class="text-xs text-gray-400 mb-2">Quick amounts:</p>
              <div class="grid grid-cols-4 gap-1">
                <button
                  class="btn btn-sm btn-secondary text-xs"
                  on:click={() => tradeAmount = 10}
                  disabled={submitting}
                >
                  $100
                </button>
                <button
                  class="btn btn-sm btn-secondary text-xs"
                  on:click={() => tradeAmount = 50}
                  disabled={submitting}
                >
                  $500
                </button>
                <button
                  class="btn btn-sm btn-secondary text-xs"
                  on:click={() => tradeAmount = 100}
                  disabled={submitting}
                >
                  $1K
                </button>
                <button
                  class="btn btn-sm btn-secondary text-xs"
                  on:click={() => tradeAmount = Math.floor(tournamentBalance / 40)} 
                  disabled={submitting}
                >
                  25%
                </button>
              </div>
            </div>

            <!-- Position Explanation -->
            <div class="p-3 bg-blue-500/10 rounded-lg">
              <h4 class="font-medium text-sm mb-1">📚 How It Works</h4>
              <ul class="text-xs text-gray-300 space-y-1">
                <li><strong>📈 Long:</strong> Profit when attention score increases</li>
                <li><strong>📉 Short:</strong> Profit when attention score decreases</li>
                <li><strong>🎯 Score:</strong> Based on Google Trends data</li>
                <li><strong>🏆 Winner:</strong> Highest portfolio value wins</li>
              </ul>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .card {
    @apply bg-gray-900/50 border border-gray-800 rounded-xl p-6 shadow-xl;
  }
  
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-opacity-50;
  }
  
  .btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed;
  }
  
  .btn-secondary {
    @apply bg-gray-700 text-gray-300 hover:bg-gray-600 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed;
  }
  
  .btn-success {
    @apply bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed;
  }
  
  .btn-danger {
    @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed;
  }

  .btn-warning {
    @apply bg-yellow-600 text-white hover:bg-yellow-700 focus:ring-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed;
  }

  .btn-sm {
    @apply px-2 py-1 text-sm;
  }
  
  .input {
    @apply bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full;
  }
</style>