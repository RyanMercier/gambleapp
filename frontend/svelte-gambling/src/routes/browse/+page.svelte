<!-- frontend/svelte-gambling/src/routes/browse/+page.svelte -->
<script>
  import { onMount } from 'svelte';
  import AttentionChart from '$lib/AttentionChart.svelte';

  // Updated target types for new categories
  let targetTypes = [
    { value: 'politician', label: '🏛️ Politicians', icon: '🏛️' },
    { value: 'celebrity', label: '🌟 Celebrities', icon: '🌟' },
    { value: 'country', label: '🌍 Countries', icon: '🌍' },
    { value: 'game', label: '🎮 Games', icon: '🎮' },
    { value: 'stock', label: '📈 Stocks', icon: '📈' },
    { value: 'crypto', label: '₿ Crypto', icon: '₿' }
  ];

  // State variables
  let searchQuery = '';
  let targetType = 'politician';
  let loading = false;
  let searchResults = null;
  let popularTargets = [];
  let selectedTarget = null;
  
  // Chart state
  let showChart = false;
  let chartTargetId = null;
  let chartTargetName = '';
  
  // Autocomplete state
  let autocompleteResults = [];
  let showAutocomplete = false;
  let autocompleteLoading = false;
  let selectedIndex = -1;
  
  // Debounce timer for autocomplete
  let debounceTimer;

  onMount(async () => {
    await loadPopularTargets();
  });

  async function loadPopularTargets() {
    try {
      const response = await fetch('/api/targets?limit=12');
      const data = await response.json();
      
      if (Array.isArray(data)) {
        popularTargets = data;
      }
    } catch (error) {
      console.error('Failed to load popular targets:', error);
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
      const response = await fetch(
        `/api/autocomplete/${backendCategory}?q=${encodeURIComponent(searchQuery)}&limit=10`
      );
      const data = await response.json();
      
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
    showAutocomplete = false;

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          query: searchQuery,
          target_type: targetType
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Search failed');
      }

      const data = await response.json();
      
      if (data.success && data.target) {
        searchResults = {
          id: data.target.id,
          query: searchQuery,
          current_attention_score: data.target.current_attention_score,
          name: data.target.name,
          type: data.target.type,
          description: data.target.description
        };

        // Show chart
        chartTargetId = data.target.id;
        chartTargetName = data.target.name;
        showChart = true;

      } else {
        throw new Error(data.message || 'No data found');
      }

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
                class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
              
              <!-- Autocomplete Dropdown -->
              {#if showAutocomplete}
                <div class="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-white/20 rounded-lg shadow-xl z-50 max-h-60 overflow-y-auto">
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
                          <div class="text-sm text-gray-400 truncate">{item.description}</div>
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

        <!-- Search Results -->
        {#if searchResults}
          <div class="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-lg font-semibold">{searchResults.name}</h3>
              <span class="text-2xl font-bold text-blue-400">
                {formatNumber(searchResults.current_attention_score)}
              </span>
            </div>
            <p class="text-gray-400 text-sm mb-4">{searchResults.description}</p>
            
            <!-- Trading Buttons -->
            <!-- <TradingButtons 
              targetId={searchResults.id}
              targetName={searchResults.name}
              currentScore={searchResults.current_attention_score}
            /> -->
          </div>
        {/if}
      </form>
    </div>

    <!-- Popular Targets -->
    {#if popularTargets.length > 0}
      <div class="card mb-8">
        <h2 class="text-xl font-semibold mb-4">🔥 Popular Targets</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {#each popularTargets as target}
            <button
              class="p-4 border border-white/20 rounded-lg hover:border-blue-500/50 transition-colors text-left group"
              on:click={() => selectPopularTarget(target)}
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span class="text-xl">{getTypeIcon(target.type)}</span>
                  <span class="font-medium group-hover:text-blue-400 transition-colors">
                    {target.name}
                  </span>
                </div>
                <span class="text-lg font-bold text-blue-400">
                  {formatNumber(target.current_attention_score)}
                </span>
              </div>
              <div class="text-xs text-gray-500 uppercase">{target.type}</div>
            </button>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Chart Section -->
    {#if showChart && chartTargetId}
      <div class="card">
        <h2 class="text-xl font-semibold mb-4">📈 {chartTargetName} - Attention Trends</h2>
        <AttentionChart targetId={chartTargetId} />
      </div>
    {/if}
  </div>
</div>

<style>
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-all duration-200;
  }
  
  .btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed;
  }
  
  .btn-secondary {
    @apply bg-white/10 text-gray-300 hover:bg-white/20 hover:text-white;
  }
  
  .card {
    @apply bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6;
  }
</style>