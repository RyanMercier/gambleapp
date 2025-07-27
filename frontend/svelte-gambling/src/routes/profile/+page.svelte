<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let predictions = [];
  let loading = true;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    try {
      const data = await apiFetch('/predictions/my');
      predictions = data;
    } catch (error) {
      console.error('Failed to load predictions:', error);
    } finally {
      loading = false;
    }
  });

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
  }

  function formatCurrency(amount) {
    return `${parseFloat(amount).toFixed(2)}`;
  }
</script>

<svelte:head>
  <title>Profile - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-4xl mx-auto">
    <!-- Profile Header -->
    <div class="card mb-8">
      <div class="flex items-center gap-6">
        <div class="w-20 h-20 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-2xl text-white font-bold">
          {$user?.username.charAt(0).toUpperCase()}
        </div>
        <div>
          <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            {$user?.username}
          </h1>
          <p class="text-gray-400">Forecasting Expert • Member since {formatDate($user?.created_at || new Date())}</p>
        </div>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="card text-center">
        <div class="text-3xl font-bold text-blue-400 mb-2">{formatCurrency($user?.balance || 0)}</div>
        <div class="text-sm text-gray-400">Current Balance</div>
      </div>
      
      <div class="card text-center">
        <div class="text-3xl font-bold text-emerald-400 mb-2">{$user?.total_predictions || 0}</div>
        <div class="text-sm text-gray-400">Total Predictions</div>
      </div>
      
      <div class="card text-center">
        <div class="text-3xl font-bold text-indigo-400 mb-2">{$user?.correct_predictions || 0}</div>
        <div class="text-sm text-gray-400">Correct Predictions</div>
      </div>
      
      <div class="card text-center">
        <div class="text-3xl font-bold text-cyan-400 mb-2">{$user?.accuracy_rate?.toFixed(1) || '0.0'}%</div>
        <div class="text-sm text-gray-400">Accuracy Rate</div>
      </div>
    </div>

    <!-- Predictions History -->
    <div class="card">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-semibold">Prediction History</h2>
        <div class="text-sm text-gray-400">{predictions.length} total predictions</div>
      </div>
      
      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="w-8 h-8 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
        </div>
      {:else if predictions.length > 0}
        <div class="space-y-4">
          {#each predictions as prediction}
            <div class="flex items-center justify-between p-4 bg-white/5 rounded-lg">
              <div class="flex-1">
                <div class="font-medium mb-1">Trend #{prediction.trend_id}</div>
                <div class="text-sm text-gray-400 mb-2">
                  Prediction: {prediction.prediction ? 'Will reach target' : 'Won\'t reach target'}
                </div>
                <div class="flex items-center gap-4 text-xs text-gray-500">
                  <span>Confidence: {prediction.confidence}/10</span>
                  <span>Staked: {formatCurrency(prediction.stake_amount)}</span>
                  <span>Created: {formatDate(prediction.created_at)}</span>
                </div>
              </div>
              <div class="text-right">
                <div class="text-lg font-medium mb-1">
                  {#if prediction.is_resolved}
                    {formatCurrency(prediction.payout_amount)}
                  {:else}
                    {formatCurrency(prediction.potential_payout)}
                  {/if}
                </div>
                <div class="text-sm px-3 py-1 rounded-full {prediction.is_resolved ? 
                  (prediction.is_correct ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400') : 
                  'bg-yellow-500/20 text-yellow-400'}">
                  {prediction.is_resolved ? 
                    (prediction.is_correct ? 'Correct' : 'Incorrect') : 
                    'Pending'}
                </div>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="text-center py-12">
          <div class="text-6xl mb-4">🔮</div>
          <h3 class="text-xl font-semibold mb-2">No predictions yet</h3>
          <p class="text-gray-400 mb-4">Start making predictions to track your forecasting skills</p>
          <a href="/trends" class="btn btn-primary">
            Browse Trends
          </a>
        </div>
      {/if}
    </div>
  </div>
</div>