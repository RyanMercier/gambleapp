<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let predictions = [];
  let recentTrends = [];
  let leaderboard = [];
  let loading = true;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    try {
      const [predictionsData, trendsData, leaderboardData] = await Promise.all([
        apiFetch('/predictions/my'),
        apiFetch('/trends?limit=5'),
        apiFetch('/leaderboard')
      ]);

      predictions = predictionsData.slice(0, 5);
      recentTrends = trendsData.slice(0, 5);
      leaderboard = leaderboardData.slice(0, 5);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
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
  <title>Dashboard - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
        Dashboard
      </h1>
      <p class="text-gray-400">Welcome back, {$user?.username || 'Predictor'}! Here's your forecasting overview.</p>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    {:else}
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="card text-center">
          <div class="text-2xl font-bold text-blue-400 mb-1">{formatCurrency($user?.balance || 0)}</div>
          <div class="text-sm text-gray-400">Current Balance</div>
        </div>
        
        <div class="card text-center">
          <div class="text-2xl font-bold text-emerald-400 mb-1">{$user?.total_predictions || 0}</div>
          <div class="text-sm text-gray-400">Total Predictions</div>
        </div>
        
        <div class="card text-center">
          <div class="text-2xl font-bold text-indigo-400 mb-1">{$user?.correct_predictions || 0}</div>
          <div class="text-sm text-gray-400">Correct Predictions</div>
        </div>
        
        <div class="card text-center">
          <div class="text-2xl font-bold text-cyan-400 mb-1">{$user?.accuracy_rate?.toFixed(1) || '0.0'}%</div>
          <div class="text-sm text-gray-400">Accuracy Rate</div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Recent Predictions -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">Recent Predictions</h2>
            <a href="/profile" class="text-blue-400 hover:text-blue-300 text-sm">View All</a>
          </div>
          
          {#if predictions.length > 0}
            <div class="space-y-4">
              {#each predictions as prediction}
                <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                  <div class="flex-1">
                    <div class="font-medium text-sm">Trend #{prediction.trend_id}</div>
                    <div class="text-xs text-gray-400">
                      Prediction: {prediction.prediction ? 'Will reach target' : 'Won\'t reach target'}
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-sm font-medium">{formatCurrency(prediction.stake_amount)}</div>
                    <div class="text-xs {prediction.is_resolved ? 
                      (prediction.is_correct ? 'text-emerald-400' : 'text-red-400') : 
                      'text-gray-400'}">
                      {prediction.is_resolved ? 
                        (prediction.is_correct ? 'Correct' : 'Incorrect') : 
                        'Pending'}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-3xl mb-2">🔮</div>
              <p>No predictions yet. <a href="/trends" class="text-blue-400 hover:text-blue-300">Start forecasting!</a></p>
            </div>
          {/if}
        </div>

        <!-- Active Trends -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">Active Trends</h2>
            <a href="/trends" class="text-blue-400 hover:text-blue-300 text-sm">View All</a>
          </div>
          
          {#if recentTrends.length > 0}
            <div class="space-y-4">
              {#each recentTrends as trend}
                <div class="p-3 bg-white/5 rounded-lg">
                  <div class="font-medium text-sm mb-1">{trend.title}</div>
                  <div class="text-xs text-gray-400 mb-2">{trend.description.slice(0, 80)}...</div>
                  <div class="flex items-center justify-between">
                    <div class="text-xs text-gray-500">Deadline: {formatDate(trend.deadline)}</div>
                    <a href="/trends/{trend.id}" class="btn btn-secondary text-xs px-3 py-1">
                      Predict
                    </a>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-3xl mb-2">📈</div>
              <p>No active trends available</p>
            </div>
          {/if}
        </div>
      </div>

      <!-- Leaderboard -->
      <div class="card mt-8">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold">Top Predictors</h2>
          <span class="text-sm text-gray-400">Ranked by accuracy</span>
        </div>
        
        {#if leaderboard.length > 0}
          <div class="space-y-3">
            {#each leaderboard as leader, index}
              <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-sm font-bold">
                    #{leader.rank}
                  </div>
                  <div>
                    <div class="font-medium text-sm">{leader.username}</div>
                    <div class="text-xs text-gray-400">{leader.total_predictions} predictions</div>
                  </div>
                </div>
                <div class="text-right">
                  <div class="text-sm font-medium text-emerald-400">{leader.accuracy_rate}%</div>
                  <div class="text-xs text-gray-400">{leader.correct_predictions} correct</div>
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <div class="text-center py-8 text-gray-400">
            <div class="text-3xl mb-2">🏆</div>
            <p>Leaderboard is empty. Be the first to make predictions!</p>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>