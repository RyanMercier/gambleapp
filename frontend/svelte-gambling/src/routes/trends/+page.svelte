<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let trends = [];
  let categories = [];
  let selectedCategory = null;
  let loading = true;
  let showPredictionModal = false;
  let selectedTrend = null;
  let predictionForm = {
    prediction: true,
    confidence: 5,
    stake_amount: 10
  };

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    try {
      const [trendsData, categoriesData] = await Promise.all([
        apiFetch('/trends'),
        apiFetch('/trends/categories')
      ]);

      trends = trendsData;
      categories = categoriesData;
    } catch (error) {
      console.error('Failed to load trends:', error);
    } finally {
      loading = false;
    }
  });

  async function filterByCategory(categoryId) {
    selectedCategory = categoryId;
    loading = true;
    
    try {
      const query = categoryId ? `?category_id=${categoryId}` : '';
      const data = await apiFetch(`/trends${query}`);
      trends = data;
    } catch (error) {
      console.error('Failed to filter trends:', error);
    } finally {
      loading = false;
    }
  }

  function openPredictionModal(trend) {
    selectedTrend = trend;
    showPredictionModal = true;
  }

  function closePredictionModal() {
    showPredictionModal = false;
    selectedTrend = null;
    predictionForm = {
      prediction: true,
      confidence: 5,
      stake_amount: 10
    };
  }

  async function submitPrediction() {
    if (!selectedTrend) return;

    try {
      await apiFetch('/predictions', {
        method: 'POST',
        body: JSON.stringify({
          trend_id: selectedTrend.id,
          ...predictionForm
        })
      });

      // Update user balance
      const updatedUser = await apiFetch('/auth/me');
      user.set(updatedUser);

      closePredictionModal();
      alert('Prediction submitted successfully!');
    } catch (error) {
      alert('Failed to submit prediction: ' + error.message);
    }
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
  }

  function formatCurrency(amount) {
    return `${parseFloat(amount).toFixed(2)}`;
  }

  function getTimeRemaining(deadline) {
    const now = new Date();
    const end = new Date(deadline);
    const diff = end - now;
    
    if (diff <= 0) return 'Ended';
    
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    
    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h`;
  }
</script>

<svelte:head>
  <title>Trends - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
        Active Trends
      </h1>
      <p class="text-gray-400">Discover and predict outcomes across various categories</p>
    </div>

    <!-- Category Filter -->
    <div class="mb-8">
      <div class="flex items-center gap-2 flex-wrap">
        <button
          class="btn {selectedCategory === null ? 'btn-primary' : 'btn-secondary'} text-sm"
          on:click={() => filterByCategory(null)}
        >
          All Categories
        </button>
        {#each categories as category}
          <button
            class="btn {selectedCategory === category.id ? 'btn-primary' : 'btn-secondary'} text-sm"
            on:click={() => filterByCategory(category.id)}
          >
            {category.icon} {category.name}
          </button>
        {/each}
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    {:else if trends.length === 0}
      <div class="text-center py-12">
        <div class="text-6xl mb-4">📈</div>
        <h3 class="text-xl font-semibold mb-2">No trends available</h3>
        <p class="text-gray-400">Check back later for new prediction opportunities</p>
      </div>
    {:else}
      <!-- Trends Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {#each trends as trend}
          <div class="trend-card">
            <div class="flex items-start justify-between mb-4">
              <div class="flex-1">
                <h3 class="font-semibold text-lg mb-2">{trend.title}</h3>
                <p class="text-gray-400 text-sm mb-3">{trend.description}</p>
              </div>
              <div class="trend-status active ml-2">
                Active
              </div>
            </div>

            <!-- Trend Details -->
            <div class="space-y-2 mb-4">
              {#if trend.current_value !== null}
                <div class="flex justify-between text-sm">
                  <span class="text-gray-400">Current Value:</span>
                  <span class="font-medium">{trend.current_value}</span>
                </div>
              {/if}
              {#if trend.target_value !== null}
                <div class="flex justify-between text-sm">
                  <span class="text-gray-400">Target Value:</span>
                  <span class="font-medium">{trend.target_value}</span>
                </div>
              {/if}
              <div class="flex justify-between text-sm">
                <span class="text-gray-400">Deadline:</span>
                <span class="font-medium">{formatDate(trend.deadline)}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-400">Time Remaining:</span>
                <span class="font-medium text-orange-400">{getTimeRemaining(trend.deadline)}</span>
              </div>
            </div>

            <!-- Action Button -->
            <button
              class="btn btn-primary w-full"
              on:click={() => openPredictionModal(trend)}
            >
              🔮 Make Prediction
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<!-- Prediction Modal -->
{#if showPredictionModal && selectedTrend}
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
    <div class="card max-w-md w-full">
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-semibold">Make Prediction</h3>
        <button 
          class="text-gray-400 hover:text-white"
          on:click={closePredictionModal}
        >
          ✕
        </button>
      </div>

      <!-- Trend Info -->
      <div class="mb-6 p-3 bg-white/5 rounded-lg">
        <h4 class="font-medium mb-2">{selectedTrend.title}</h4>
        <p class="text-sm text-gray-400 mb-2">{selectedTrend.description}</p>
        <div class="text-xs text-gray-500">
          Deadline: {formatDate(selectedTrend.deadline)}
        </div>
      </div>

      <!-- Prediction Form -->
      <form on:submit|preventDefault={submitPrediction} class="space-y-4">
        <!-- Prediction Choice -->
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-3">
            Your Prediction
          </label>
          <div class="grid grid-cols-2 gap-2">
            <button
              type="button"
              class="btn {predictionForm.prediction ? 'btn-success' : 'btn-secondary'}"
              on:click={() => predictionForm.prediction = true}
            >
              ✅ Will Reach Target
            </button>
            <button
              type="button"
              class="btn {!predictionForm.prediction ? 'btn-danger' : 'btn-secondary'}"
              on:click={() => predictionForm.prediction = false}
            >
              ❌ Won't Reach Target
            </button>
          </div>
        </div>

        <!-- Confidence Level -->
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">
            Confidence Level: {predictionForm.confidence}/10
          </label>
          <input
            type="range"
            min="1"
            max="10"
            bind:value={predictionForm.confidence}
            class="w-full"
          />
        </div>

        <!-- Stake Amount -->
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-2">
            Stake Amount
          </label>
          <input
            type="number"
            min="1"
            max={$user?.balance || 0}
            step="0.01"
            bind:value={predictionForm.stake_amount}
            class="input"
            placeholder="Enter stake amount"
            required
          />
          <div class="text-xs text-gray-400 mt-1">
            Available balance: {formatCurrency($user?.balance || 0)}
          </div>
        </div>

        <!-- Potential Payout -->
        <div class="p-3 bg-blue-500/10 rounded-lg">
          <div class="flex justify-between text-sm">
            <span>Potential Payout:</span>
            <span class="font-medium text-blue-400">
              {formatCurrency(predictionForm.stake_amount * 2)}
            </span>
          </div>
        </div>

        <!-- Submit -->
        <div class="flex gap-2">
          <button
            type="button"
            class="btn btn-secondary flex-1"
            on:click={closePredictionModal}
          >
            Cancel
          </button>
          <button
            type="submit"
            class="btn btn-primary flex-1"
          >
            Submit Prediction
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}