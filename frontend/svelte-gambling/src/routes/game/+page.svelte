<script>
  import { onMount } from "svelte";
  let game;

  onMount(async () => {
    const Phaser = await import("phaser");
    const Colyseus = await import("colyseus.js");

    const client = new Colyseus.Client("ws://localhost:2567");
    const room = await client.joinOrCreate("balance");

    const config = {
      type: Phaser.AUTO,
      parent: "phaser-container",
      backgroundColor: "#222",
      physics: {
        default: "matter",
        matter: {
          gravity: { y: 1 },
          debug: true,
        },
      },
      scale: {
        mode: Phaser.Scale.RESIZE,
        autoCenter: Phaser.Scale.CENTER_BOTH,
        width: "100%",
        height: "100%",
      },
      scene: {
        preload() {},

        create() {
          const scene = this;

          // Ground
          scene.matter.add.rectangle(400, 580, 800, 40, { isStatic: true });

          // Player stick
          const stick = scene.matter.add.rectangle(400, 500, 20, 120, {
            chamfer: { radius: 5 },
            inertia: Infinity,
            friction: 0.9,
            frictionAir: 0.1,
          });

          const plates = [];
          const otherPlayers = {};

          // Input movement
          scene.input.on("pointermove", (pointer) => {
            const targetX = Phaser.Math.Clamp(pointer.x, 50, 750);
            scene.matter.body.setPosition(stick, { x: targetX, y: 500 });
            scene.matter.body.setVelocity(stick, { x: 0, y: 0 });
          });

          // Send player position
          scene.time.addEvent({
            delay: 50,
            loop: true,
            callback: () => {
              room.send("update", { x: stick.position.x, y: stick.position.y });
            },
          });

          // Listen for plates
          room.onMessage("spawn_plate", (data) => {
            const plate = scene.matter.add.rectangle(data.x, 0, 80, 10, {
              chamfer: { radius: 2 },
              friction: 0.5,
              frictionAir: 0.3,
              restitution: 0.1,
            });
            plates.push(plate);
          });

          // ⭐️ THE CORRECT WAY: Wait for state to be ready
          room.onStateChange.once((state) => {
            console.log("Initial state received");
            console.log("players:", state.players);
            console.log("players.constructor.name:", state.players?.constructor?.name);

            state.players.onAdd = (player, sessionId) => {
              if (sessionId === room.sessionId) return;
              console.log(`Player joined: ${sessionId}`);

              const graphics = scene.add.graphics();
              graphics.fillStyle(0x999999, 0.5);
              graphics.fillRect(-10, -60, 20, 120);

              const container = scene.add.container(player.x, player.y);
              container.add(graphics);
              otherPlayers[sessionId] = container;

              player.onChange = () => {
                if (otherPlayers[sessionId]) {
                  otherPlayers[sessionId].setPosition(player.x, player.y);
                }
              };
            };

            state.players.onRemove = (player, sessionId) => {
              console.log(`Player left: ${sessionId}`);
              if (otherPlayers[sessionId]) {
                otherPlayers[sessionId].destroy();
                delete otherPlayers[sessionId];
              }
            };

            // Add any already-existing players
            state.players.forEach((player, sessionId) => {
              if (sessionId === room.sessionId) return;

              console.log(`Existing player: ${sessionId}`);

              const graphics = scene.add.graphics();
              graphics.fillStyle(0x999999, 0.5);
              graphics.fillRect(-10, -60, 20, 120);

              const container = scene.add.container(player.x, player.y);
              container.add(graphics);
              otherPlayers[sessionId] = container;

              player.onChange = () => {
                if (otherPlayers[sessionId]) {
                  otherPlayers[sessionId].setPosition(player.x, player.y);
                }
              };
            });
          });

          // Winner
          room.onMessage("winner", () => {
            alert("Game over! We have a winner!");
          });

          // Detect loss
          scene.matter.world.on("afterupdate", () => {
            if (stick.position.y > 700 || plates.some((p) => p.position.y > 700)) {
              room.send("dead");
            }
          });
        },

        update() {},
      },
    };

    game = new Phaser.Game(config);
  });
</script>

<div id="phaser-container" class="phaser-wrapper"></div>

<style>
  .phaser-wrapper {
    width: 97%;
    height: 92%;
    padding: 1rem;
    box-sizing: border-box;
  }
</style>
