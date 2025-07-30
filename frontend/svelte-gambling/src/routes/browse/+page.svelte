<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';
  import AttentionChart from '$lib/AttentionChart.svelte';

  let searchQuery = '';
  let targetType = 'politician';
  let searchResults = null;
  let loading = false;
  let popularTargets = [];
  let selectedTarget = null;

  // Chart-specific variables
  let showChart = false;
  let chartTargetId = null;
  let chartTargetName = '';

  const targetTypes = [
    { value: 'politician', label: '🏛️ Politicians', icon: '🏛️' },
    { value: 'billionaire', label: '💰 Billionaires', icon: '💰' },
    { value: 'country', label: '🌍 Countries', icon: '🌍' },
    { value: 'stock', label: '📈 Meme Stocks', icon: '📈' }
  ];

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    // Load popular targets
    try {
      const targets = await apiFetch('/targets');
      popularTargets = targets.slice(0, 20);
      console.log('Loaded popular targets:', popularTargets.length);
    } catch (error) {
      console.error('Failed to load popular targets:', error);
    }
  });

  async function searchTrends() {
    if (!searchQuery.trim()) return;
    
    loading = true;
    // Hide chart while loading
    showChart = false;
    chartTargetId = null;

    try {
      const data = await apiFetch('/search', {
        method: 'POST',
        body: JSON.stringify({
          query: searchQuery.trim(),
          target_type: targetType
        })
      });

      console.log('Search results:', data);
      
      // Handle different possible response formats
      let targetId;
      if (data.id) {
        targetId = data.id;
      } else if (data.id) {
        targetId = data.id;
      } else if (data.target && data.target.id) {
        targetId = data.target.id;
      } else {
        console.error('No target ID found in search response:', data);
        alert('Search failed: No target ID returned');
        return;
      }

      searchResults = {
        id: targetId,
        query: searchQuery.trim(),
        current_attention_score: data.current_attention_score || data.attention_score || 0,
        name: data.name || searchQuery.trim(),
        type: targetType
      };

      // Show chart with the target
      chartTargetId = targetId;
      chartTargetName = searchResults.name;
      showChart = true;

    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed: ' + error.message);
    } finally {
      loading = false;
    }
  }

  async function selectPopularTarget(target) {
    console.log('Selecting popular target:', target);
    
    selectedTarget = target;
    searchQuery = target.name;
    targetType = target.type;
    
    // Set search results for trading buttons
    searchResults = {
      id: target.id,
      query: target.name,
      current_attention_score: target.current_attention_score || 0,
      name: target.name,
      type: target.type
    };

    // Show chart with the selected target
    chartTargetId = target.id;
    chartTargetName = target.name;
    showChart = true;
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
    const typeObj = targetTypes.find(t => t.value === type);
    return typeObj ? typeObj.icon : '📊';
  }
</script>

<svelte:head>
  <title>Browse Attention Trends - TrendBet</title>
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
            <button class="btn btn-success" on:click={() => goto(`/trade/${searchResults.id}?type=buy`)}>
              📈 Buy Shares
            </button>
            <button class="btn btn-danger" on:click={() => goto(`/trade/${searchResults.id}?type=sell`)}>
              📉 Sell Shares
            </button>
          </div>
        </div>
        
        <!-- Use AttentionChart Component -->
        {#if showChart && chartTargetId}
          <div class="mt-4">
            <AttentionChart 
              targetId={chartTargetId} 
              targetName={chartTargetName}
              height="400px"
              showTimeframeSelector={true}
              autoUpdate={false}
            />
          </div>
        {:else}
          <div class="h-96 bg-gray-800/50 rounded-lg p-4 flex items-center justify-center">
            <div class="text-center text-gray-400">
              <div class="text-4xl mb-2">📊</div>
              <div>Chart will appear here when you select a target</div>
            </div>
          </div>
        {/if}
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
                  <span class="font-medium">{formatNumber(target.current_attention_score)}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-400">Updated:</span>
                  <span class="font-medium text-blue-400">
                    {target.last_updated ? new Date(target.last_updated).toLocaleDateString() : 'Never'}
                  </span>
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

<style>
  .card {
    @apply bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6 shadow-xl;
  }
  
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-opacity-50;
  }
  
  .btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500;
  }
  
  .btn-secondary {
    @apply bg-gray-700 text-gray-300 hover:bg-gray-600 focus:ring-gray-500;
  }
  
  .btn-success {
    @apply bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500;
  }
  
  .btn-danger {
    @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
  }
  
  .input {
    @apply bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent;
  }
  
  button:disabled {
    @apply opacity-50 cursor-not-allowed;
  }
</style>