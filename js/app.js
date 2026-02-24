/**
 * Benicia Tile Matcher - Main Application
 * Wires together game engine, map, and UI
 */

(function () {
  "use strict";

  function init() {
    UI.init();

    // Initialize map with zone click handler
    MapController.init("map-container", handleZoneClick);

    // Initialize game engine
    GameEngine.init(handleStateChange);

    // Button handlers
    document.getElementById("btn-start").addEventListener("click", startGame);
    document.getElementById("fact-next-btn").addEventListener("click", handleNextTile);
    document.getElementById("btn-play-again").addEventListener("click", startGame);
    document.getElementById("btn-share").addEventListener("click", shareResults);

    // Show welcome screen
    UI.showScreen("welcome");
  }

  function startGame() {
    MapController.resetMap();
    GameEngine.startGame();
    UI.showScreen("game");

    // Leaflet needs a refresh after the game screen becomes visible
    if (MapController.refresh) MapController.refresh();

    const tile = GameEngine.getCurrentTile();
    if (tile) {
      UI.showTile(tile, GameEngine.getProgress());
    }
    UI.updateHUD(GameEngine.getState());
  }

  function handleZoneClick(zoneId) {
    const result = GameEngine.guess(zoneId);
    if (!result) return;

    if (result.correct) {
      // Flash the incorrect zone red first if auto-revealed
      if (result.autoRevealed) {
        MapController.flashIncorrect(zoneId);
      }
      MapController.flashCorrect(result.tile.zoneId);
      UI.animateScoreChange(result.pointsEarned);
      UI.updateHUD(GameEngine.getState());

      // Short delay then show fact card
      setTimeout(() => {
        UI.showFactCard(result);
      }, result.autoRevealed ? 700 : 400);
    } else {
      MapController.flashIncorrect(zoneId);

      // Generate directional hint
      const currentTile = GameEngine.getCurrentTile();
      const hint = MapController.highlightHint(currentTile, zoneId);
      UI.showHint(hint);
    }
  }

  function handleNextTile() {
    UI.hideFactCard();

    const hasMore = GameEngine.nextTile();
    if (hasMore) {
      const tile = GameEngine.getCurrentTile();
      if (tile) {
        UI.showTile(tile, GameEngine.getProgress());
      }
      UI.updateHUD(GameEngine.getState());
    } else {
      // Game complete
      const results = GameEngine.getResults();
      UI.showResults(results);
      saveHighScore(results.score);
    }
  }

  function handleStateChange(gameState) {
    // Could be used for additional state-driven updates
  }

  function saveHighScore(score) {
    try {
      const prev = parseInt(localStorage.getItem("benicia-tiles-highscore") || "0");
      if (score > prev) {
        localStorage.setItem("benicia-tiles-highscore", score.toString());
      }
    } catch (e) {
      // localStorage not available
    }
  }

  function shareResults() {
    const results = GameEngine.getResults();
    const text =
      `Benicia Tile Matcher ${results.grade.emoji}\n` +
      `Score: ${results.score.toLocaleString()} (${results.grade.name})\n` +
      `Accuracy: ${results.accuracy}% | Best Streak: ${results.bestStreak}\n` +
      `Time: ${results.timeFormatted}\n` +
      `Learn about Benicia's history: beniciahistory.org/First-Street-Tiles`;

    if (navigator.share) {
      navigator.share({ text }).catch(() => {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById("btn-share");
        const original = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => {
          btn.textContent = original;
        }, 2000);
      });
    }
  }

  // Start when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
