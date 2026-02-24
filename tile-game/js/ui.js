/**
 * Benicia Tile Matcher - UI Controller
 * Manages screen transitions, tile card, fact popup, score display
 */

const UI = (function () {
  // Screen elements
  let screens = {};
  let elements = {};

  function $(id) {
    return document.getElementById(id);
  }

  function formatScore(score) {
    return score.toLocaleString();
  }

  return {
    init() {
      screens = {
        welcome: $("screen-welcome"),
        game: $("screen-game"),
        results: $("screen-results"),
      };

      elements = {
        // Game HUD
        score: $("hud-score"),
        streak: $("hud-streak"),
        progress: $("hud-progress"),
        progressBar: $("hud-progress-bar"),

        // Tile card
        tileImage: $("tile-image"),
        tileName: $("tile-name"),
        tileNumber: $("tile-number"),

        // Hint area
        hintArea: $("hint-area"),
        hintText: $("hint-text"),

        // Fact modal
        factModal: $("fact-modal"),
        factImage: $("fact-image"),
        factName: $("fact-name"),
        factLocation: $("fact-location"),
        factText: $("fact-text"),
        factLearnMore: $("fact-learn-more"),
        factPoints: $("fact-points"),
        factNextBtn: $("fact-next-btn"),

        // Results
        resultGradeEmoji: $("result-grade-emoji"),
        resultGradeName: $("result-grade-name"),
        resultScore: $("result-score"),
        resultAccuracy: $("result-accuracy"),
        resultStreak: $("result-streak"),
        resultTime: $("result-time"),
        resultFirstTries: $("result-first-tries"),
      };
    },

    showScreen(name) {
      Object.values(screens).forEach((s) => s.classList.remove("active"));
      if (screens[name]) {
        screens[name].classList.add("active");
      }
    },

    updateHUD(gameState) {
      elements.score.textContent = formatScore(gameState.score);
      elements.streak.textContent = gameState.streak > 0 ? `${gameState.streak}x` : "";
      elements.streak.classList.toggle("on-fire", gameState.streak >= 3);
      elements.progress.textContent = `${gameState.matchedCount} / ${gameState.total}`;

      const pct = (gameState.matchedCount / gameState.total) * 100;
      elements.progressBar.style.width = `${pct}%`;
    },

    showTile(tile, progress) {
      elements.tileImage.src = tile.image;
      elements.tileImage.alt = tile.name;
      elements.tileName.textContent = tile.name;
      elements.tileNumber.textContent = `#${tile.id}`;
      elements.hintArea.classList.remove("visible");

      // Animate tile card entrance
      const card = document.querySelector(".tile-card");
      card.classList.remove("slide-in");
      // Force reflow
      void card.offsetWidth;
      card.classList.add("slide-in");
    },

    showHint(hintText) {
      elements.hintText.textContent = hintText;
      elements.hintArea.classList.add("visible");
    },

    showFactCard(result) {
      const tile = result.tile;

      elements.factImage.src = tile.image;
      elements.factImage.alt = tile.name;
      elements.factName.textContent = tile.name;
      elements.factLocation.textContent = tile.address;
      elements.factText.textContent = tile.fact;
      elements.factLearnMore.href = tile.learnMoreUrl;

      if (result.autoRevealed) {
        elements.factPoints.textContent = "No points - better luck next time!";
        elements.factPoints.className = "fact-points zero";
      } else {
        let pointsText = `+${result.pointsEarned} points`;
        if (result.multiplier > 1) {
          pointsText += ` (${result.multiplier}x streak bonus!)`;
        }
        if (result.attempts === 1) {
          pointsText += " \u2014 First try!";
        }
        elements.factPoints.textContent = pointsText;
        elements.factPoints.className = "fact-points";
        if (result.multiplier > 1) {
          elements.factPoints.classList.add("multiplied");
        }
      }

      elements.factModal.classList.add("visible");

      // Check if this is the last tile
      const gameState = GameEngine.getState();
      if (gameState.matchedCount >= gameState.total) {
        elements.factNextBtn.textContent = "See Results";
      } else {
        elements.factNextBtn.textContent = "Next Tile \u2192";
      }
    },

    hideFactCard() {
      elements.factModal.classList.remove("visible");
    },

    showResults(results) {
      elements.resultGradeEmoji.textContent = results.grade.emoji;
      elements.resultGradeName.textContent = results.grade.name;
      elements.resultScore.textContent = formatScore(results.score);
      elements.resultAccuracy.textContent = `${results.accuracy}%`;
      elements.resultStreak.textContent = results.bestStreak;
      elements.resultTime.textContent = results.timeFormatted;
      elements.resultFirstTries.textContent = `${results.firstTries} / ${results.totalTiles}`;

      this.showScreen("results");
    },

    animateScoreChange(points) {
      if (points <= 0) return;

      const floater = document.createElement("span");
      floater.className = "score-floater";
      floater.textContent = `+${points}`;
      elements.score.parentElement.appendChild(floater);

      setTimeout(() => floater.remove(), 1000);
    },
  };
})();
