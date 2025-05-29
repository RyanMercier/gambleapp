<script>
  import { goto } from '$app/navigation';

  function startGame() {
    goto('/game');
  }
</script>

<section class="flex flex-col items-center justify-center h-full text-center bg-[#1a1a1d] rounded-2xl p-12 shadow-lg">
  <h1 class="text-5xl font-bold mb-6 text-purple-400">Welcome to Gamble Royale</h1>
  <p class="text-lg mb-8 text-gray-300 max-w-xl">The ultimate test of skill, luck, and strategy. Compete against players, climb the leaderboards, and win big!</p>
  <button on:click={startGame} class="px-8 py-4 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition font-semibold">
    Enter the Arena
  </button>
</section>