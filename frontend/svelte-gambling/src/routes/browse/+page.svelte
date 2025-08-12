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
  let featuredTargets = [];
  let selectedTarget = null;

  // Chart-specific variables
  let showChart = false;
  let chartTargetId = null;
  let chartTargetName = '';

  let showAutocomplete = false;
  let autocompleteResults = [];
  let autocompleteLoading = false;
  let debounceTimer = null;
  let selectedIndex = -1;

  // Updated target types to match backend
  const targetTypes = [
    { value: 'politician', label: '🏛️ Politicians', icon: '🏛️' },
    { value: 'celebrity', label: '🌟 Celebrities', icon: '🌟' },
    { value: 'country', label: '🌍 Countries', icon: '🌍' },
    { value: 'game', label: '🎮 Games', icon: '🎮' },
    { value: 'stock', label: '📈 Stocks', icon: '📈' },
    { value: 'crypto', label: '₿ Crypto', icon: '₿' }
  ];

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    await loadFeaturedTargets();
  });

  async function loadFeaturedTargets() {
    try {
      const targets = await apiFetch('/targets?limit=12');
      featuredTargets = Array.isArray(targets) ? targets : [];
      console.log('Loaded featured targets:', featuredTargets.length);
    } catch (error) {
      console.error('Failed to load featured targets:', error);
      featuredTargets = [];
    }
  }

  // Autocomplete functionality
  async function handleSearchInput() {
    clearTimeout(debounceTimer);
    
    if (searchQuery.length < 2) {
      showAutocomplete = false;
      autocompleteResults = [];
      return;
    }

    debounceTimer = setTimeout(async () => {
      await fetchAutocompleteResults();
    }, 300); // 300ms debounce
  }

  async function fetchAutocompleteResults() {
    if (autocompleteLoading) return;
    
    autocompleteLoading = true;
    selectedIndex = -1;
    
    try {
      // Map frontend category to backend category
      const categoryMap = {
        'politician': 'politicians',
        'celebrity': 'celebrities',
        'country': 'countries', 
        'game': 'games',
        'stock': 'stocks',
        'crypto': 'crypto'
      };
      
      const backendCategory = categoryMap[targetType];
      const data = await apiFetch(`/api/autocomplete/${backendCategory}?q=${encodeURIComponent(searchQuery)}&limit=10`);
      
      if (data.success) {
        autocompleteResults = data.suggestions;
        showAutocomplete = autocompleteResults.length > 0;
      } else {
        autocompleteResults = [];
        showAutocomplete = false;
      }
    } catch (error) {
      console.error('Autocomplete error:', error);
      autocompleteResults = [];
      showAutocomplete = false;
    } finally {
      autocompleteLoading = false;
    }
  }

  function selectAutocompleteItem(item) {
    searchQuery = item.name;
    showAutocomplete = false;
    autocompleteResults = [];
    selectedIndex = -1;
    
    // Automatically search when item is selected
    searchTrends();
  }

  function handleKeydown(event) {
    if (!showAutocomplete) return;
    
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, autocompleteResults.length - 1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        break;
      case 'Enter':
        event.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < autocompleteResults.length) {
          selectAutocompleteItem(autocompleteResults[selectedIndex]);
        } else {
          searchTrends();
        }
        break;
      case 'Escape':
        showAutocomplete = false;
        selectedIndex = -1;
        break;
    }
  }

  // Hide autocomplete when clicking outside
  function handleClickOutside() {
    setTimeout(() => {
      showAutocomplete = false;
      selectedIndex = -1;
    }, 150); // Small delay to allow for clicks on autocomplete items
  }

  async function searchTrends() {
    if (!searchQuery.trim()) {
      alert('Please enter a search term');
      return;
    }
    
    loading = true;
    showChart = false;
    chartTargetId = null;
    showAutocomplete = false;

    try {
      const data = await apiFetch('/api/search', {
        method: 'POST',
        body: JSON.stringify({
          query: searchQuery.trim(),
          target_type: targetType
        })
      });

      console.log('Search results:', data);
      
      // Handle the response format from the updated backend
      if (data.success && data.target) {
        searchResults = {
          id: data.target.id,
          query: searchQuery.trim(),
          current_attention_score: data.target.current_attention_score,
          name: data.target.name,
          type: data.target.type,
          description: data.target.description
        };

        // Show chart with the target
        chartTargetId = data.target.id;
        chartTargetName = data.target.name;
        showChart = true;

      } else {
        throw new Error(data.message || 'Search failed');
      }

    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed: ' + error.message);
    } finally {
      loading = false;
    }
  }

  // Update category when changed
  function handleCategoryChange(newCategory) {
    targetType = newCategory;
    // Clear autocomplete when category changes
    showAutocomplete = false;
    autocompleteResults = [];
    selectedIndex = -1;
    
    // Trigger new autocomplete search if there's a query
    if (searchQuery.length >= 2) {
      handleSearchInput();
    }
  }

  async function selectFeaturedTarget(target) {
    console.log('Exploring featured target:', target);
    
    selectedTarget = target;
    searchQuery = target.name;
    targetType = target.type;
    
    // Set search results for potential trading
    searchResults = {
      id: target.id,
      query: target.name,
      current_attention_score: target.current_attention_score || 0,
      name: target.name,
      type: target.type,
      description: target.description
    };

    // Show chart to encourage exploration
    chartTargetId = target.id;
    chartTargetName = target.name;
    showChart = true;
    
    // Scroll to chart to encourage viewing
    setTimeout(() => {
      const chartElement = document.querySelector('.chart-section');
      if (chartElement) {
        chartElement.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);
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
      <p class="text-gray-400">Search curated targets and see their attention score over time. Trade attention like stocks!</p>
    </div>

    <!-- Search Section -->
    <div class="card mb-8">
      <h2 class="text-xl font-semibold mb-4">🔍 Search Trends</h2>
      
      <form on:submit|preventDefault={searchTrends} class="space-y-4">
        <!-- Target Type Selection -->
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">Category</label>
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            {#each targetTypes as type}
              <button
                type="button"
                class="btn {targetType === type.value ? 'btn-primary' : 'btn-secondary'} text-sm"
                on:click={() => handleCategoryChange(type.value)}
              >
                {type.label}
              </button>
            {/each}
          </div>
        </div>

        <!-- Search Input with Autocomplete -->
        <div class="relative">
          <div class="flex gap-2">
            <div class="relative flex-1">
              <input
                type="text"
                bind:value={searchQuery}
                on:input={handleSearchInput}
                on:keydown={handleKeydown}
                on:blur={handleClickOutside}
                placeholder="Start typing to search..."
                class="input w-full"
                disabled={loading}
              />
              
              <!-- Autocomplete Dropdown -->
              {#if showAutocomplete}
                <div class="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-white/20 rounded-lg shadow-xl z-[9999] max-h-60 overflow-y-auto">
                  {#if autocompleteLoading}
                    <div class="p-3 text-center text-gray-400">
                      <div class="w-4 h-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin mx-auto"></div>
                    </div>
                  {:else if autocompleteResults.length > 0}
                    {#each autocompleteResults as item, index}
                      <button
                        type="button"
                        class="w-full text-left p-3 hover:bg-white/10 border-b border-white/10 last:border-b-0 {selectedIndex === index ? 'bg-blue-600/20' : ''}"
                        on:mousedown|preventDefault={() => selectAutocompleteItem(item)}
                      >
                        <div class="font-medium">{item.name}</div>
                        {#if item.description}
                          <div class="relative z-500 text-sm text-gray-400 truncate">{item.description}</div>
                        {/if}
                      </button>
                    {/each}
                  {:else}
                    <div class="p-3 text-gray-400 text-center">No matches found</div>
                  {/if}
                </div>
              {/if}
            </div>
            
            <button
              type="submit"
              class="btn btn-primary px-8"
              disabled={loading || !searchQuery.trim()}
            >
              {#if loading}
                <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              {:else}
                Search
              {/if}
            </button>
          </div>
          
          <p class="text-xs text-gray-500 mt-2">
            💡 Only pre-approved targets can be traded to prevent manipulation
          </p>
        </div>
      </form>
    </div>

    <!-- Search Results / Chart Section -->
    {#if searchResults}
      <div class="card mb-8">
        <div class="flex items-center justify-between mb-6">
          <!-- FIXED: Single Trade Button -->
          <div class="flex justify-center">
            <button 
              class="btn btn-primary px-8 py-3"
              on:click={() => goto(`/trade/${searchResults.id}`)}
            >
              💱 Trade
            </button>
          </div>
        </div>
        
        <!-- Chart Component -->
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
              <div>Chart will appear here when you select a target</div>
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Featured Targets Section -->
    <div class="card relative">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-semibold">🌟 Featured Targets</h2>
        <div class="flex items-center gap-2">
          <button 
            class="btn btn-secondary text-sm"
            on:click={loadFeaturedTargets}
            disabled={loading}
          >
            🔄 Refresh
          </button>
          <p class="text-sm text-gray-400">Click to explore • Watch trends • Then trade</p>
        </div>
      </div>
      
      {#if featuredTargets.length > 0}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {#each featuredTargets as target}
            <div class="featured-target-card group">
              <!-- Explore Button (Main Action) -->
              <button
                class="explore-btn"
                on:click={() => selectFeaturedTarget(target)}
              >
                <div class="flex items-center gap-3 mb-2">
                  <span class="text-2xl">{getTypeIcon(target.type)}</span>
                  <div class="flex-1 min-w-0">
                    <h3 class="font-medium truncate group-hover:text-blue-400 transition-colors">
                      {target.name}
                    </h3>
                    <p class="text-xs text-gray-400 capitalize">{target.type}</p>
                  </div>
                  <div class="explore-icon">
                    📊
                  </div>
                </div>
                
                <div class="space-y-1">
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-400">Attention:</span>
                    <span class="font-medium text-blue-400">{formatNumber(target.current_attention_score)}</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-400">Trend:</span>
                    <span class="text-xs text-green-400">Click to explore →</span>
                  </div>
                </div>
              </button>

              <!-- Quick Trade Button (Secondary Action) -->
              <div class="trade-actions">
                <button
                  class="btn btn-outline btn-sm"
                  on:click|stopPropagation={() => goto(`/trade/${target.id}`)}
                  title="Quick trade without exploring"
                >
                  ⚡ Quick Trade
                </button>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <!-- Empty state same as before -->
      {/if}
    </div>
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
    @apply bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500;
  }
  
  .btn-danger {
    @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
  }
  
  .input {
    @apply bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent;
  }

  /* Add these styles to the browse page <style> section */

  .featured-target-card {
    @apply relative p-4 bg-white/5 rounded-lg border border-white/10 hover:border-blue-500/30 transition-all duration-300;
  }

  .explore-btn {
    @apply w-full text-left p-0 bg-transparent border-none focus:outline-none cursor-pointer;
  }

  .explore-icon {
    @apply text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity duration-300 text-lg;
  }

  .trade-actions {
    @apply mt-3 pt-3 border-t border-white/10 flex gap-2;
  }

  .btn-outline {
    @apply border border-gray-600 text-gray-300 hover:border-blue-500 hover:text-blue-400 hover:bg-blue-500/10;
  }

  .btn-sm {
    @apply px-3 py-1.5 text-xs;
  }

  /* Chart section styling */
  .chart-section {
    @apply scroll-mt-6;
  }

  /* Featured target hover effects */
  .featured-target-card:hover {
    @apply bg-white/10 shadow-lg scale-[1.02];
  }

  .featured-target-card:hover .explore-btn h3 {
    @apply text-blue-400;
  }

  /* Pulse animation for featured targets */
  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    50% { box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1); }
  }

  .featured-target-card:hover {
    animation: pulse-glow 2s infinite;
  }
</style>