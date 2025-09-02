# 🎮 Gravity Flip Runner

A thrilling 2D side-scrolling game where you control gravity to navigate through challenging obstacles!

## 🌟 Game Features

### 🔄 **Core Gravity Flip Mechanic**
- **SPACE** to flip gravity between floor and ceiling
- Smooth 180° camera rotation animation
- Strategic timing required to avoid obstacles

### 🚧 **Dual-Layer Obstacle System**
- **Static Spikes**: Red rectangular obstacles
- **Rotating Blades**: Orange spinning obstacles that rotate continuously
- **Moving Spikes**: Purple obstacles that move up and down
- **Electric Walls**: Cyan obstacles with animated electric effects

### 💥 **Breakable Platforms**
- Green platforms that break after you step on them
- Visual warning system (flashing red before breaking)
- Forces quick decision-making and movement

### 💎 **Collectible System**
- **Coins** (Yellow): Worth 10 points each
- **Orbs** (Purple): Worth 50 points each
- Smooth bobbing and rotation animations
- Contribute to score with combo multipliers

### ⚡ **Power-ups & Power-downs**
**Power-ups (Helpful):**
- 🐌 **Slow Motion**: Slows down time
- 🛡️ **Shield**: Temporary invulnerability
- 🔄 **Auto Flip**: Safety assistance
- 💰 **Double Coins**: 2x coin collection

**Power-downs (Challenging):**
- 🔄 **Inverted Controls**: Left becomes right
- 🎲 **Random Flips**: Unpredictable gravity changes
- 🌑 **Blackout**: Limited visibility

### 🌍 **Dynamic Environment Themes**
Themes automatically change every 30 seconds:
- 🏙️ **City**: Urban skyline with building silhouettes
- 🌆 **Cyberpunk**: Neon grid with purple/pink colors
- 🌿 **Jungle**: Green vines and natural elements
- 🚀 **Space**: Starfield with cosmic colors

### 🔥 **Combo & Streak System**
- Chain gravity flips for increasing multipliers
- **3+ flips**: 2x score multiplier
- **5+ flips**: 3x score multiplier
- Visual combo counter shows current streak

## 🎮 Controls

| Key | Action |
|-----|--------|
| **SPACE** | Flip gravity / Start game / Restart |
| **A** or **←** | Move left |
| **D** or **→** | Move right |
| **ESC** | Pause/Resume/Quit |
| **R** | Restart (on game over) |

## 🚀 How to Run

### Option 1: Windowed Mode (Requires Display)
```bash
python3 gravity_flip_runner_windowed.py
```

### Option 2: Demo Mode (Works Everywhere)
```bash
python3 gravity_flip_runner.py
```

### Option 3: Test Mechanics
```bash
python3 test_game.py
```

## 📋 Requirements

- Python 3.6+
- Pygame library

### Installing Pygame:

**Ubuntu/Debian:**
```bash
sudo apt install python3-pygame
```

**Other Systems:**
```bash
pip install pygame
```

## 🎯 Gameplay Tips

1. **Master the Flip**: Time your gravity flips to avoid obstacles on both sides
2. **Chain Combos**: Multiple flips in succession increase your score multiplier
3. **Collect Everything**: Coins and orbs boost your score significantly
4. **Use Platforms Wisely**: Breakable platforms provide temporary safety but break quickly
5. **Manage Power-ups**: Some power-ups help, others make the game more challenging
6. **Adapt to Themes**: Each environment theme brings unique visual challenges

## 🏆 Scoring System

- **Base Score**: Increases with distance traveled
- **Collectibles**: Coins (10 pts) and Orbs (50 pts)
- **Combo Multipliers**: 1x → 2x → 3x based on flip streaks
- **Power-up Bonuses**: Double coins power-up doubles collectible values

## 🔧 Game Mechanics Details

### Gravity System
- Smooth physics simulation with realistic gravity
- Instant gravity reversal with momentum preservation
- Ground detection for both floor and ceiling

### Obstacle Generation
- Procedural spawning system
- Balanced difficulty progression
- Multiple obstacle types with unique behaviors

### Theme System
- Automatic theme progression
- Visual variety to maintain engagement
- Theme-specific background animations

### Power-up System
- Temporary effects with visual timers
- Balanced mix of helpful and challenging effects
- Strategic collection decisions

## 🎨 Visual Features

- **Smooth Animations**: Fluid camera rotation and object movement
- **Visual Feedback**: Player flashing during invulnerability
- **Dynamic Backgrounds**: Theme-specific animated backgrounds
- **UI Elements**: Real-time score, combo, and power-up displays
- **Visual Effects**: Rotating collectibles, electric sparks, platform warnings

## 🔮 Future Enhancements

Potential additions for future versions:
- Sound effects and background music
- Particle effects for collisions and power-ups
- Achievement system
- Leaderboards and high scores
- Additional obstacle types
- More power-ups and abilities
- Level editor
- Multiplayer modes

---

**Enjoy playing Gravity Flip Runner!** 🚀✨