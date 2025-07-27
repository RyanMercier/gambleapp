<script>
  import { createEventDispatcher } from 'svelte';
  import apiFetch from '$lib/api';
  import { user } from '$lib/stores';
  
  export let trend = null;
  export let isOpen = false;
  
  const dispatch = createEventDispatcher();
  
  let predictionForm = {
    prediction: true,
    confidence: 5,
    stake_amount: 10
  };
  let submitting = false;
  let error = '';

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
  }

  function formatCurrency(amount) {
    return `${parseFloat(amount).toFixed(2)}`;
  }

  function close() {
    isOpen = false;
    error = '';
    predictionForm = {
      prediction: true,
      confidence: 5,
      stake_amount: 10
    };
    dispatch('close');
  }

  async function submitPrediction() {
    if (!trend || submitting) return;

    submitting = true;
    error = '';

    try {
      await apiFetch('/predictions', {
        method: 'POST',
        body: JSON.stringify({
          trend_id: trend.id,
          ...predictionForm
        })
      });

      // Update user balance
      const updatedUser = await apiFetch('/auth/me');
      user.set(updatedUser);

      dispatch('success', {
        message: 'Prediction submitted successfully!',
        prediction: predictionForm
      });
      
      close();
    } catch (err) {
      error = err.message || 'Failed to submit prediction';
    } finally {
      submitting = false;
    }
  }

  // Close modal when clicking outside
  function handleBackdropClick(event) {
    if (event.target === event.currentTarget) {
      close();
    }
  }
</script>

{#if isOpen && trend}
  <div 
    class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
    on:click={handleBackdropClick}
    role="dialog"
    aria-modal="true"
    aria-labelledby="modal-title"
  >
    <div class="card max-w-md w-full" on:click|stopPropagation>
      <div class="flex items-center justify-between mb-6">
        <h3 id="modal-title" class="text-xl font-semibold">Make Prediction</h3>
        <button 
          class="text-gray-400 hover:text-white transition-colors"
          on:click={close}
          aria-label="Close modal"
        >
          ✕
        </button>
      </div>

      <!-- Trend Info -->
      <div class="mb-6 p-3 bg-white/5 rounded-lg">
        <h4 class="font-medium mb-2">{trend.title}</h4>
        <p class="text-sm text-gray-400 mb-2">{trend.description}</p>
        <div class="text-xs text-gray-500">
          Deadline: {formatDate(trend.deadline)}
        </div>
      </div>

      <!-- Error Message -->
      {#if error}
        <div class="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      {/if}

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
              class="btn {predictionForm.prediction ? 'btn-success' : 'btn-secondary'} transition-all"
              on:click={() => predictionForm.prediction = true}
              disabled={submitting}
            >
              ✅ Will Reach Target
            </button>
            <button
              type="button"
              class="btn {!predictionForm.prediction ? 'btn-danger' : 'btn-secondary'} transition-all"
              on:click={() => predictionForm.prediction = false}
              disabled={submitting}
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
            class="w-full accent-blue-500"
            disabled={submitting}
          />
          <div class="flex justify-between text-xs text-gray-500 mt-1">
            <span>Low</span>
            <span>High</span>
          </div>
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
            disabled={submitting}
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
          <div class="text-xs text-gray-400 mt-1">
            2:1 payout ratio
          </div>
        </div>

        <!-- Submit -->
        <div class="flex gap-2">
          <button
            type="button"
            class="btn btn-secondary flex-1"
            on:click={close}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            class="btn btn-primary flex-1"
            disabled={submitting}
          >
            {#if submitting}
              <div class="flex items-center justify-center gap-2">
                <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Submitting...
              </div>
            {:else}
              Submit Prediction
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}