/**
 * Benicia Tile Matcher - Game Engine
 * Manages game state, scoring, streaks, and progression
 */

const GameEngine = (function () {
  // Game states
  const STATE = {
    IDLE: "idle",
    PLAYING: "playing",
    SHOWING_FACT: "showing_fact",
    COMPLETE: "complete",
  };

  // Scoring constants
  const SCORE = {
    BASE: 100,
    FIRST_TRY_BONUS: 50,
    SECOND_TRY_BONUS: 25,
    STREAK_THRESHOLD_2X: 3,
    STREAK_THRESHOLD_3X: 5,
    MAX_ATTEMPTS: 3,
  };

  // Grade thresholds (percentage of max possible score)
  const GRADES = [
    { name: "Historian", emoji: "\u{1F3DB}\uFE0F", minPercent: 90 },
    { name: "Gold", emoji: "\u{1F947}", minPercent: 70 },
    { name: "Silver", emoji: "\u{1F948}", minPercent: 50 },
    { name: "Bronze", emoji: "\u{1F949}", minPercent: 0 },
  ];

  let state = STATE.IDLE;
  let tiles = [];
  let currentIndex = 0;
  let score = 0;
  let streak = 0;
  let bestStreak = 0;
  let attempts = 0;
  let totalFirstTries = 0;
  let matchedTileIds = new Set();
  let startTime = null;
  let onStateChange = null;

  function shuffle(array) {
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function getMultiplier() {
    if (streak >= SCORE.STREAK_THRESHOLD_3X) return 3;
    if (streak >= SCORE.STREAK_THRESHOLD_2X) return 2;
    return 1;
  }

  function calculateMaxScore() {
    // Max score = every tile correct on first try with max streak
    // First 2 tiles: 150 * 1 = 300
    // Tile 3-4: 150 * 2 = 300
    // Tiles 5-28: 150 * 3 = 3600
    // Total: 300 + 300 + 3600 = 4200
    return TILES.length * (SCORE.BASE + SCORE.FIRST_TRY_BONUS) * 2; // approximate
  }

  function getStateInternal() {
    const elapsed = startTime ? Date.now() - startTime : 0;
    const maxScore = 4200;
    const percent = maxScore > 0 ? (score / maxScore) * 100 : 0;
    const grade = GRADES.find((g) => percent >= g.minPercent) || GRADES[GRADES.length - 1];

    return {
      state,
      score,
      streak,
      bestStreak,
      currentIndex,
      total: tiles.length,
      progress: tiles.length > 0 ? currentIndex / tiles.length : 0,
      accuracy: currentIndex > 0 ? Math.round((totalFirstTries / currentIndex) * 100) : 0,
      elapsed,
      grade,
      matchedCount: matchedTileIds.size,
    };
  }

  function notify() {
    if (onStateChange) {
      onStateChange(getStateInternal());
    }
  }

  // Public API
  return {
    init(callback) {
      onStateChange = callback;
    },

    startGame() {
      tiles = shuffle(TILES);
      currentIndex = 0;
      score = 0;
      streak = 0;
      bestStreak = 0;
      attempts = 0;
      totalFirstTries = 0;
      matchedTileIds = new Set();
      startTime = Date.now();
      state = STATE.PLAYING;
      notify();
    },

    getCurrentTile() {
      if (currentIndex < tiles.length) {
        return tiles[currentIndex];
      }
      return null;
    },

    getProgress() {
      return {
        current: currentIndex + 1,
        total: tiles.length,
      };
    },

    guess(zoneId) {
      if (state !== STATE.PLAYING) return null;

      const currentTile = tiles[currentIndex];
      attempts++;

      const isCorrect = zoneId === currentTile.zoneId;

      if (isCorrect) {
        // Calculate score for this match
        let pointsEarned = SCORE.BASE;
        if (attempts === 1) {
          pointsEarned += SCORE.FIRST_TRY_BONUS;
          streak++;
          totalFirstTries++;
        } else if (attempts === 2) {
          pointsEarned += SCORE.SECOND_TRY_BONUS;
          streak = 0;
        } else {
          streak = 0;
        }

        // Apply multiplier
        const multiplier = getMultiplier();
        pointsEarned *= multiplier;

        score += pointsEarned;
        if (streak > bestStreak) bestStreak = streak;
        matchedTileIds.add(currentTile.id);

        state = STATE.SHOWING_FACT;
        notify();

        return {
          correct: true,
          tile: currentTile,
          pointsEarned,
          multiplier,
          attempts,
          streak,
        };
      } else {
        // Wrong answer
        const attemptsLeft = SCORE.MAX_ATTEMPTS - attempts;

        if (attemptsLeft <= 0) {
          // Auto-reveal after max attempts
          matchedTileIds.add(currentTile.id);
          streak = 0;
          state = STATE.SHOWING_FACT;
          notify();

          return {
            correct: true, // forced reveal
            tile: currentTile,
            pointsEarned: 0,
            multiplier: 1,
            attempts,
            streak: 0,
            autoRevealed: true,
          };
        }

        notify();
        return {
          correct: false,
          attemptsLeft,
          attempts,
          hint: currentTile.hint,
        };
      }
    },

    nextTile() {
      currentIndex++;
      attempts = 0;

      if (currentIndex >= tiles.length) {
        state = STATE.COMPLETE;
        notify();
        return false;
      }

      state = STATE.PLAYING;
      notify();
      return true;
    },

    isMatched(tileId) {
      return matchedTileIds.has(tileId);
    },

    getMatchedIds() {
      return new Set(matchedTileIds);
    },

    getState() {
      return getStateInternal();
    },

    getResults() {
      const elapsed = startTime ? Date.now() - startTime : 0;
      const minutes = Math.floor(elapsed / 60000);
      const seconds = Math.floor((elapsed % 60000) / 1000);
      const maxScore = 4200;
      const percent = maxScore > 0 ? (score / maxScore) * 100 : 0;
      const grade = GRADES.find((g) => percent >= g.minPercent) || GRADES[GRADES.length - 1];

      return {
        score,
        bestStreak,
        accuracy: tiles.length > 0 ? Math.round((totalFirstTries / tiles.length) * 100) : 0,
        timeFormatted: `${minutes}:${seconds.toString().padStart(2, "0")}`,
        grade,
        totalTiles: tiles.length,
        firstTries: totalFirstTries,
      };
    },

    STATE,
  };
})();
