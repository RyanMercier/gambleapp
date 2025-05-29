<script>
  import { goto } from '$app/navigation';
  import apiFetch from '$lib/api';
  let username = '';
  let email = '';
  let password = '';
  let error = '';
  let mode = 'login';

  async function submit() {
    error = '';
    const endpoint = mode === 'login' ? '/login' : '/register';
    const payload = mode === 'login'
      ? { username, password }
      : { username, email, password };

    try {
      const data = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      if (!data?.token || !data?.username || !data?.id) {
        throw new Error('Incomplete user data from server');
      }

      // Save token and user
      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify({
        id: data.id,
        username: data.username,
      }));

      goto('/');
    } catch (err) {
      error = err.message || 'Something went wrong';
    }
  }
</script>

<section class="max-w-md mx-auto mt-16 p-6 bg-gray-800 text-white rounded-2xl shadow-lg">
  <h1 class="text-2xl font-bold mb-4">{mode === 'login' ? 'Login' : 'Register'}</h1>

  <form on:submit|preventDefault={submit} class="space-y-4">
    <input
      class="w-full px-4 py-2 rounded-xl bg-gray-700 text-white border border-gray-600 focus:outline-none focus:border-purple-400 text-sm"
      placeholder="Username"
      bind:value={username}
      required
      autocomplete="username"
    />

    {#if mode === 'register'}
      <input
        type="email"
        class="w-full px-4 py-2 rounded-xl bg-gray-700 text-white border border-gray-600 focus:outline-none focus:border-purple-400 text-sm"
        placeholder="Email"
        bind:value={email}
        required
        autocomplete="email"
      />
    {/if}

    <input
      type="password"
      class="w-full px-4 py-2 rounded-xl bg-gray-700 text-white border border-gray-600 focus:outline-none focus:border-purple-400 text-sm"
      placeholder="Password"
      bind:value={password}
      required
      autocomplete={mode === 'login' ? 'current-password' : 'new-password'}
    />

    <button
      type="submit"
      class="w-full py-2 bg-purple-600 hover:bg-purple-700 rounded-xl font-semibold text-sm transition text-black"
    >
      {mode === 'login' ? 'Login' : 'Register'}
    </button>

    {#if error}
      <div class="text-red-400 text-sm mt-2">{error}</div>
    {/if}
  </form>

  <p class="mt-4 text-sm text-gray-300">
    {mode === 'login' ? 'Need an account?' : 'Already have an account?'}
    <a
      href="#"
      on:click={(e) => { e.preventDefault(); mode = mode === 'login' ? 'register' : 'login'; error = ''; }}
      class="underline ml-1 cursor-pointer hover:text-purple-400"
    >
      {mode === 'login' ? 'Register here' : 'Login'}
    </a>
  </p>
</section>
