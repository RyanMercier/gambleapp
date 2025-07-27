<script>
  import { goto } from '$app/navigation';
  import apiFetch from '$lib/api';
  import { user } from '$lib/stores';
  
  let username = '';
  let email = '';
  let password = '';
  let error = '';
  let loading = false;
  let mode = 'login';

  async function submit() {
    if (loading) return;
    
    error = '';
    loading = true;
    
    const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
    const payload = mode === 'login'
      ? { username, password }
      : { username, email, password };

    try {
      const data = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      if (!data?.token || !data?.user) {
        throw new Error('Incomplete response from server');
      }

      // Save token and user data
      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      user.set(data.user);

      console.log('✅ Authentication successful');
      goto('/dashboard');
      
    } catch (err) {
      console.error('❌ Authentication failed:', err);
      error = err.message || 'Something went wrong';
    } finally {
      loading = false;
    }
  }

  function switchMode() {
    mode = mode === 'login' ? 'register' : 'login';
    error = '';
    username = '';
    email = '';
    password = '';
  }
</script>

<svelte:head>
  <title>{mode === 'login' ? 'Login' : 'Register'} - TrendBet</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
  <!-- Background Animation -->
  <div class="absolute inset-0 opacity-20">
    <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse"></div>
    <div class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse" style="animation-delay: 1s;"></div>
  </div>

  <!-- Login/Register Form -->
  <div class="relative z-10 w-full max-w-md">
    <div class="card">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
          {mode === 'login' ? 'Welcome Back' : 'Join TrendBet'}
        </h1>
        <p class="text-gray-400">
          {mode === 'login' 
            ? 'Sign in to continue trading attention' 
            : 'Create your account and start trading'}
        </p>
      </div>

      <!-- Form -->
      <form on:submit|preventDefault={submit} class="space-y-4">
        <!-- Username -->
        <div>
          <label for="username" class="block text-sm font-medium text-gray-300 mb-2">
            Username
          </label>
          <input
            id="username"
            type="text"
            class="input"
            placeholder="Enter your username"
            bind:value={username}
            required
            autocomplete="username"
            disabled={loading}
          />
        </div>

        <!-- Email (Register only) -->
        {#if mode === 'register'}
          <div>
            <label for="email" class="block text-sm font-medium text-gray-300 mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              class="input"
              placeholder="Enter your email"
              bind:value={email}
              required
              autocomplete="email"
              disabled={loading}
            />
          </div>
        {/if}

        <!-- Password -->
        <div>
          <label for="password" class="block text-sm font-medium text-gray-300 mb-2">
            Password
          </label>
          <input
            id="password"
            type="password"
            class="input"
            placeholder="Enter your password"
            bind:value={password}
            required
            autocomplete={mode === 'login' ? 'current-password' : 'new-password'}
            disabled={loading}
          />
        </div>

        <!-- Error Message -->
        {#if error}
          <div class="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        {/if}

        <!-- Submit Button -->
        <button
          type="submit"
          class="btn btn-primary w-full text-lg py-3 font-semibold"
          disabled={loading}
        >
          {#if loading}
            <div class="flex items-center justify-center gap-2">
              <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              {mode === 'login' ? 'Signing in...' : 'Creating account...'}
            </div>
          {:else}
            {mode === 'login' ? '📈 Sign In & Trade' : '🚀 Create Account'}
          {/if}
        </button>

        <!-- Mode Switch -->
        <div class="text-center pt-4 border-t border-white/10">
          <p class="text-gray-400 text-sm">
            {mode === 'login' ? "Don't have an account?" : "Already have an account?"}
            <button
              type="button"
              class="text-blue-400 hover:text-blue-300 font-medium ml-1 underline"
              on:click={switchMode}
              disabled={loading}
            >
              {mode === 'login' ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
      </form>
    </div>

    <!-- Benefits -->
    <div class="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="text-center p-4 bg-white/5 rounded-lg">
        <div class="text-2xl mb-2">📊</div>
        <div class="text-xs text-gray-400">Real-Time Data</div>
      </div>
      <div class="text-center p-4 bg-white/5 rounded-lg">
        <div class="text-2xl mb-2">💱</div>
        <div class="text-xs text-gray-400">Instant Trading</div>
      </div>
      <div class="text-center p-4 bg-white/5 rounded-lg">
        <div class="text-2xl mb-2">🏆</div>
        <div class="text-xs text-gray-400">Tournaments</div>
      </div>
    </div>

    <!-- Demo Account Info -->
    <div class="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg text-center">
      <p class="text-blue-300 text-sm mb-2">
        <strong>Demo Account Available</strong>
      </p>
      <p class="text-gray-400 text-xs">
        Username: <code>admin</code> • Password: <code>admin123</code>
      </p>
    </div>
  </div>
</div>