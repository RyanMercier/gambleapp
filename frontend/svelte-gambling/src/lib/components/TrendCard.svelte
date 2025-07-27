<script>
  export let trend;
  export let onPredict = null;
  
  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
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
  
  function getProgressPercentage() {
    if (!trend.current_value || !trend.target_value) return 0;
    return Math.min((trend.current_value / trend.target_value) * 100, 100);
  }
</script>

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

  <!-- Progress Bar (if current/target values exist) -->
  {#if trend.current_value !== null && trend.target_value !== null}
    <div class="mb-4">
      <div class="flex justify-between text-sm mb-2">
        <span class="text-gray-400">Progress to Target</span>
        <span class="font-medium">{getProgressPercentage().toFixed(1)}%</span>
      </div>
      <div class="w-full bg-gray-700 rounded-full h-2">
        <div 
          class="bg-gradient-to-r from-blue-500 to-indigo-500 h-2 rounded-full transition-all duration-300"
          style="width: {getProgressPercentage()}%"
        ></div>
      </div>
    </div>
  {/if}

  <!-- Trend Details -->
  <div class="space-y-2 mb-4">
    {#if trend.current_value !== null}
      <div class="flex justify-between text-sm">
        <span class="text-gray-400">Current Value:</span>
        <span class="font-medium">{trend.current_value.toLocaleString()}</span>
      </div>
    {/if}
    {#if trend.target_value !== null}
      <div class="flex justify-between text-sm">
        <span class="text-gray-400">Target Value:</span>
        <span class="font-medium">{trend.target_value.toLocaleString()}</span>
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
  {#if onPredict}
    <button
      class="btn btn-primary w-full"
      on:click={() => onPredict(trend)}
    >
      🔮 Make Prediction
    </button>
  {/if}
</div>