#!/usr/bin/env python3
"""
Gravity Flip Runner - A 2D side-scrolling game with gravity manipulation mechanics

Game Features:
- Gravity flip mechanic with smooth camera rotation
- Dual-layer obstacles on floor and ceiling
- Breakable platforms
- Collectible orbs/coins
- Power-ups and power-downs
- Dynamic environment themes
- Combo and streak system

Controls:
- SPACE: Flip gravity
- A/D or Arrow Keys: Move left/right
- ESC: Pause/Menu
"""

import pygame
import math
import random
import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Initialize Pygame
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Use dummy video driver for headless environments
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (255, 0, 255)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)

# Game States
class GameState(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"

# Gravity States
class GravityState(Enum):
    NORMAL = 1
    FLIPPED = -1

# Themes
class Theme(Enum):
    CITY = "city"
    CYBERPUNK = "cyberpunk"
    JUNGLE = "jungle"
    SPACE = "space"

@dataclass
class Vector2:
    x: float
    y: float
    
    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

class Player:
    def __init__(self, x: float, y: float):
        self.pos = Vector2(x, y)
        self.velocity = Vector2(0, 0)
        self.size = 30
        self.gravity_state = GravityState.NORMAL
        self.on_ground = False
        self.can_flip = True
        self.flip_cooldown = 0
        self.invulnerable_time = 0
        self.color = BLUE
        
        # Movement constants
        self.speed = 300
        self.jump_force = 400
        self.gravity = 800
        
    def update(self, dt: float, screen_height: int):
        # Handle gravity flip cooldown
        if self.flip_cooldown > 0:
            self.flip_cooldown -= dt
            if self.flip_cooldown <= 0:
                self.can_flip = True
        
        # Handle invulnerability
        if self.invulnerable_time > 0:
            self.invulnerable_time -= dt
        
        # Apply gravity
        gravity_force = self.gravity * self.gravity_state.value
        self.velocity.y += gravity_force * dt
        
        # Update position
        self.pos.x += self.velocity.x * dt
        self.pos.y += self.velocity.y * dt
        
        # Ground collision (floor and ceiling)
        if self.gravity_state == GravityState.NORMAL:
            if self.pos.y >= screen_height - self.size:
                self.pos.y = screen_height - self.size
                self.velocity.y = 0
                self.on_ground = True
            else:
                self.on_ground = False
        else:  # Flipped gravity
            if self.pos.y <= self.size:
                self.pos.y = self.size
                self.velocity.y = 0
                self.on_ground = True
            else:
                self.on_ground = False
    
    def flip_gravity(self):
        if self.can_flip:
            self.gravity_state = GravityState.FLIPPED if self.gravity_state == GravityState.NORMAL else GravityState.NORMAL
            self.can_flip = False
            self.flip_cooldown = 0.2  # Small cooldown to prevent spam
            self.velocity.y = 0  # Reset vertical velocity
            return True
        return False
    
    def move_horizontal(self, direction: float, dt: float):
        self.velocity.x = direction * self.speed
    
    def get_rect(self):
        return pygame.Rect(self.pos.x - self.size//2, self.pos.y - self.size//2, self.size, self.size)
    
    def draw(self, screen: pygame.Surface, camera_rotation: float):
        # Create a surface for the player
        player_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        
        # Draw player with invulnerability effect
        color = self.color
        if self.invulnerable_time > 0 and int(self.invulnerable_time * 10) % 2:
            color = tuple(c // 2 for c in color)  # Dim color for flashing effect
        
        pygame.draw.circle(player_surface, color, (self.size//2, self.size//2), self.size//2)
        
        # Add direction indicator
        indicator_color = WHITE
        if self.gravity_state == GravityState.FLIPPED:
            pygame.draw.polygon(player_surface, indicator_color, 
                              [(self.size//2, self.size//4), 
                               (self.size//2 - 5, self.size//2), 
                               (self.size//2 + 5, self.size//2)])
        else:
            pygame.draw.polygon(player_surface, indicator_color, 
                              [(self.size//2, 3*self.size//4), 
                               (self.size//2 - 5, self.size//2), 
                               (self.size//2 + 5, self.size//2)])
        
        # Rotate the surface if camera is rotated
        if abs(camera_rotation) > 0.1:
            rotated_surface = pygame.transform.rotate(player_surface, camera_rotation)
            rotated_rect = rotated_surface.get_rect(center=(self.pos.x, self.pos.y))
            screen.blit(rotated_surface, rotated_rect)
        else:
            screen.blit(player_surface, (self.pos.x - self.size//2, self.pos.y - self.size//2))

class Obstacle:
    def __init__(self, x: float, y: float, width: float, height: float, obstacle_type: str = "static"):
        self.pos = Vector2(x, y)
        self.width = width
        self.height = height
        self.type = obstacle_type
        self.color = RED
        self.rotation = 0
        self.rotation_speed = 0
        self.movement_speed = 0
        self.movement_range = 0
        self.original_y = y
        
        # Set properties based on type
        if obstacle_type == "rotating_blade":
            self.rotation_speed = 180  # degrees per second
            self.color = ORANGE
        elif obstacle_type == "moving_spike":
            self.movement_speed = 100
            self.movement_range = 50
            self.color = PURPLE
        elif obstacle_type == "electric_wall":
            self.color = CYAN
    
    def update(self, dt: float, scroll_speed: float):
        # Move obstacle left with scroll speed
        self.pos.x -= scroll_speed * dt
        
        # Type-specific updates
        if self.type == "rotating_blade":
            self.rotation += self.rotation_speed * dt
        elif self.type == "moving_spike":
            self.pos.y = self.original_y + math.sin(time.time() * 3) * self.movement_range
    
    def get_rect(self):
        return pygame.Rect(self.pos.x - self.width//2, self.pos.y - self.height//2, self.width, self.height)
    
    def draw(self, screen: pygame.Surface, camera_rotation: float):
        if self.type == "rotating_blade":
            # Draw rotating blade
            center = (int(self.pos.x), int(self.pos.y))
            blade_length = self.width // 2
            angle_rad = math.radians(self.rotation + camera_rotation)
            
            end_x = center[0] + blade_length * math.cos(angle_rad)
            end_y = center[1] + blade_length * math.sin(angle_rad)
            
            pygame.draw.line(screen, self.color, center, (int(end_x), int(end_y)), 8)
            pygame.draw.circle(screen, self.color, center, 10)
        elif self.type == "electric_wall":
            # Draw electric wall with animated effect
            rect = self.get_rect()
            pygame.draw.rect(screen, self.color, rect)
            
            # Add electric effect
            for i in range(0, int(self.height), 20):
                if random.random() < 0.3:
                    spark_x = rect.x + random.randint(0, int(self.width))
                    spark_y = rect.y + i
                    pygame.draw.circle(screen, WHITE, (spark_x, spark_y), 3)
        else:
            # Draw regular obstacle
            rect = self.get_rect()
            pygame.draw.rect(screen, self.color, rect)

class BreakablePlatform:
    def __init__(self, x: float, y: float, width: float):
        self.pos = Vector2(x, y)
        self.width = width
        self.height = 20
        self.broken = False
        self.break_timer = 0
        self.break_delay = 0.5  # Time before breaking after stepped on
        self.stepped_on = False
        self.color = GREEN
    
    def update(self, dt: float, scroll_speed: float):
        self.pos.x -= scroll_speed * dt
        
        if self.stepped_on and not self.broken:
            self.break_timer += dt
            if self.break_timer >= self.break_delay:
                self.broken = True
    
    def step_on(self):
        if not self.broken and not self.stepped_on:
            self.stepped_on = True
            return True
        return False
    
    def get_rect(self):
        if self.broken:
            return pygame.Rect(0, 0, 0, 0)  # No collision when broken
        return pygame.Rect(self.pos.x - self.width//2, self.pos.y - self.height//2, self.width, self.height)
    
    def draw(self, screen: pygame.Surface, camera_rotation: float):
        if not self.broken:
            color = self.color
            if self.stepped_on:
                # Flash red when about to break
                flash_intensity = int((self.break_timer / self.break_delay) * 255)
                color = (min(255, self.color[0] + flash_intensity), 
                        max(0, self.color[1] - flash_intensity), 
                        self.color[2])
            
            rect = self.get_rect()
            pygame.draw.rect(screen, color, rect)

class Collectible:
    def __init__(self, x: float, y: float, collectible_type: str = "coin"):
        self.pos = Vector2(x, y)
        self.type = collectible_type
        self.collected = False
        self.size = 15
        self.rotation = 0
        self.bob_offset = 0
        self.color = YELLOW if collectible_type == "coin" else PURPLE
        self.value = 10 if collectible_type == "coin" else 50
    
    def update(self, dt: float, scroll_speed: float):
        self.pos.x -= scroll_speed * dt
        self.rotation += 180 * dt  # Rotate for visual effect
        self.bob_offset = math.sin(time.time() * 4) * 5  # Bobbing motion
    
    def get_rect(self):
        return pygame.Rect(self.pos.x - self.size, self.pos.y - self.size + self.bob_offset, 
                          self.size * 2, self.size * 2)
    
    def draw(self, screen: pygame.Surface, camera_rotation: float):
        if not self.collected:
            center = (int(self.pos.x), int(self.pos.y + self.bob_offset))
            pygame.draw.circle(screen, self.color, center, self.size)
            pygame.draw.circle(screen, WHITE, center, self.size, 3)

class PowerUp:
    def __init__(self, x: float, y: float, power_type: str):
        self.pos = Vector2(x, y)
        self.type = power_type
        self.collected = False
        self.size = 20
        self.duration = 5.0  # Default duration
        self.color = self._get_color()
    
    def _get_color(self):
        colors = {
            "slow_motion": CYAN,
            "auto_flip": GREEN,
            "shield": YELLOW,
            "double_coins": PURPLE,
            "inverted_controls": RED,
            "random_flips": ORANGE,
            "blackout": BLACK
        }
        return colors.get(self.type, WHITE)
    
    def update(self, dt: float, scroll_speed: float):
        self.pos.x -= scroll_speed * dt
    
    def get_rect(self):
        return pygame.Rect(self.pos.x - self.size, self.pos.y - self.size, 
                          self.size * 2, self.size * 2)
    
    def draw(self, screen: pygame.Surface, camera_rotation: float):
        if not self.collected:
            rect = self.get_rect()
            pygame.draw.rect(screen, self.color, rect)
            pygame.draw.rect(screen, WHITE, rect, 3)
            
            # Draw power-up symbol
            center = rect.center
            if self.type == "slow_motion":
                pygame.draw.circle(screen, WHITE, center, 8, 2)
            elif self.type == "shield":
                pygame.draw.circle(screen, WHITE, center, 12, 3)

class Camera:
    def __init__(self):
        self.rotation = 0
        self.target_rotation = 0
        self.rotation_speed = 360  # degrees per second
    
    def update(self, dt: float):
        # Smooth camera rotation
        rotation_diff = self.target_rotation - self.rotation
        if abs(rotation_diff) > 1:
            self.rotation += rotation_diff * 5 * dt
        else:
            self.rotation = self.target_rotation
    
    def flip(self):
        self.target_rotation = 180 if self.target_rotation == 0 else 0

class Game:
    def __init__(self):
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("Gravity Flip Runner")
        except pygame.error as e:
            print(f"Display initialization failed: {e}")
            print("Running in headless mode for demonstration...")
            self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game state
        self.state = GameState.MENU
        self.score = 0
        self.coins = 0
        self.combo_count = 0
        self.combo_multiplier = 1
        self.distance = 0
        
        # Game objects
        self.player = Player(200, SCREEN_HEIGHT // 2)
        self.camera = Camera()
        self.obstacles: List[Obstacle] = []
        self.platforms: List[BreakablePlatform] = []
        self.collectibles: List[Collectible] = []
        self.powerups: List[PowerUp] = []
        
        # Game mechanics
        self.scroll_speed = 200
        self.spawn_timer = 0
        self.spawn_interval = 2.0
        self.theme = Theme.CITY
        self.theme_timer = 0
        self.theme_duration = 30  # Change theme every 30 seconds
        
        # Active power-ups
        self.active_powerups = {}
        
        # Font for UI
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.PLAYING:
                        self.state = GameState.PAUSED
                    elif self.state == GameState.PAUSED:
                        self.state = GameState.PLAYING
                    elif self.state == GameState.MENU:
                        self.running = False
                
                elif event.key == pygame.K_SPACE:
                    if self.state == GameState.MENU:
                        self.start_game()
                    elif self.state == GameState.PLAYING:
                        if self.player.flip_gravity():
                            self.camera.flip()
                            self.combo_count += 1
                            self.update_combo_multiplier()
                    elif self.state == GameState.GAME_OVER:
                        self.reset_game()
                
                elif event.key == pygame.K_r and self.state == GameState.GAME_OVER:
                    self.reset_game()
    
    def update_combo_multiplier(self):
        if self.combo_count >= 5:
            self.combo_multiplier = 3
        elif self.combo_count >= 3:
            self.combo_multiplier = 2
        else:
            self.combo_multiplier = 1
    
    def start_game(self):
        self.state = GameState.PLAYING
        self.reset_game()
    
    def reset_game(self):
        self.score = 0
        self.coins = 0
        self.combo_count = 0
        self.combo_multiplier = 1
        self.distance = 0
        
        self.player = Player(200, SCREEN_HEIGHT // 2)
        self.camera = Camera()
        self.obstacles.clear()
        self.platforms.clear()
        self.collectibles.clear()
        self.powerups.clear()
        self.active_powerups.clear()
        
        self.scroll_speed = 200
        self.spawn_timer = 0
        self.theme = Theme.CITY
        self.theme_timer = 0
        
        self.state = GameState.PLAYING
    
    def spawn_obstacles(self, dt: float):
        self.spawn_timer += dt
        
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            
            # Spawn obstacles on both floor and ceiling
            obstacle_types = ["static", "rotating_blade", "moving_spike", "electric_wall"]
            
            # Floor obstacle
            if random.random() < 0.7:  # 70% chance
                obs_type = random.choice(obstacle_types)
                x = SCREEN_WIDTH + 50
                y = SCREEN_HEIGHT - 30
                self.obstacles.append(Obstacle(x, y, 40, 60, obs_type))
            
            # Ceiling obstacle
            if random.random() < 0.7:  # 70% chance
                obs_type = random.choice(obstacle_types)
                x = SCREEN_WIDTH + 100  # Offset to avoid same position
                y = 30
                self.obstacles.append(Obstacle(x, y, 40, 60, obs_type))
            
            # Spawn breakable platform occasionally
            if random.random() < 0.3:  # 30% chance
                x = SCREEN_WIDTH + 150
                y = random.choice([SCREEN_HEIGHT - 100, 100])  # Floor or ceiling level
                self.platforms.append(BreakablePlatform(x, y, 80))
            
            # Spawn collectibles
            if random.random() < 0.8:  # 80% chance
                x = SCREEN_WIDTH + random.randint(50, 200)
                y = random.randint(100, SCREEN_HEIGHT - 100)
                collectible_type = "orb" if random.random() < 0.3 else "coin"
                self.collectibles.append(Collectible(x, y, collectible_type))
            
            # Spawn power-ups occasionally
            if random.random() < 0.1:  # 10% chance
                x = SCREEN_WIDTH + random.randint(100, 300)
                y = random.randint(100, SCREEN_HEIGHT - 100)
                power_types = ["slow_motion", "auto_flip", "shield", "double_coins", 
                              "inverted_controls", "random_flips", "blackout"]
                power_type = random.choice(power_types)
                self.powerups.append(PowerUp(x, y, power_type))
    
    def update_theme(self, dt: float):
        self.theme_timer += dt
        if self.theme_timer >= self.theme_duration:
            self.theme_timer = 0
            themes = list(Theme)
            current_index = themes.index(self.theme)
            self.theme = themes[(current_index + 1) % len(themes)]
    
    def get_theme_colors(self):
        theme_colors = {
            Theme.CITY: {"bg": (50, 50, 100), "accent": (100, 100, 150)},
            Theme.CYBERPUNK: {"bg": (20, 0, 40), "accent": (255, 0, 255)},
            Theme.JUNGLE: {"bg": (0, 40, 0), "accent": (0, 255, 100)},
            Theme.SPACE: {"bg": (10, 10, 30), "accent": (200, 200, 255)}
        }
        return theme_colors.get(self.theme, theme_colors[Theme.CITY])
    
    def update(self, dt: float):
        if self.state != GameState.PLAYING:
            return
        
        # Handle input
        keys = pygame.key.get_pressed()
        movement = 0
        
        # Check for inverted controls power-up
        inverted = "inverted_controls" in self.active_powerups
        
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            movement = 1 if inverted else -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            movement = -1 if inverted else 1
        
        self.player.move_horizontal(movement, dt)
        
        # Update game objects
        self.player.update(dt, SCREEN_HEIGHT)
        self.camera.update(dt)
        
        # Update distance and score
        self.distance += self.scroll_speed * dt
        self.score += int(self.scroll_speed * dt * self.combo_multiplier)
        
        # Update power-ups
        self.update_powerups(dt)
        
        # Spawn new obstacles
        self.spawn_obstacles(dt)
        
        # Update obstacles
        for obstacle in self.obstacles[:]:
            obstacle.update(dt, self.scroll_speed)
            if obstacle.pos.x < -100:
                self.obstacles.remove(obstacle)
        
        # Update platforms
        for platform in self.platforms[:]:
            platform.update(dt, self.scroll_speed)
            if platform.pos.x < -100:
                self.platforms.remove(platform)
        
        # Update collectibles
        for collectible in self.collectibles[:]:
            collectible.update(dt, self.scroll_speed)
            if collectible.pos.x < -50:
                self.collectibles.remove(collectible)
        
        # Update power-ups
        for powerup in self.powerups[:]:
            powerup.update(dt, self.scroll_speed)
            if powerup.pos.x < -50:
                self.powerups.remove(powerup)
        
        # Check collisions
        self.check_collisions()
        
        # Update theme
        self.update_theme(dt)
        
        # Increase difficulty over time
        self.scroll_speed += 5 * dt
        self.spawn_interval = max(1.0, self.spawn_interval - 0.01 * dt)
    
    def update_powerups(self, dt: float):
        # Update active power-up timers
        expired_powerups = []
        for power_type, remaining_time in self.active_powerups.items():
            self.active_powerups[power_type] = remaining_time - dt
            if self.active_powerups[power_type] <= 0:
                expired_powerups.append(power_type)
        
        # Remove expired power-ups
        for power_type in expired_powerups:
            del self.active_powerups[power_type]
        
        # Apply slow motion effect
        if "slow_motion" in self.active_powerups:
            # This would affect game speed, implemented in main loop
            pass
    
    def check_collisions(self):
        player_rect = self.player.get_rect()
        
        # Check obstacle collisions
        for obstacle in self.obstacles:
            if player_rect.colliderect(obstacle.get_rect()):
                if self.player.invulnerable_time <= 0 and "shield" not in self.active_powerups:
                    self.game_over()
                    return
        
        # Check platform collisions
        for platform in self.platforms:
            if player_rect.colliderect(platform.get_rect()):
                if not platform.stepped_on:
                    platform.step_on()
                    # Player lands on platform
                    if self.player.gravity_state == GravityState.NORMAL and self.player.velocity.y > 0:
                        self.player.pos.y = platform.pos.y - platform.height//2 - self.player.size//2
                        self.player.velocity.y = 0
                        self.player.on_ground = True
                    elif self.player.gravity_state == GravityState.FLIPPED and self.player.velocity.y < 0:
                        self.player.pos.y = platform.pos.y + platform.height//2 + self.player.size//2
                        self.player.velocity.y = 0
                        self.player.on_ground = True
        
        # Check collectible collisions
        for collectible in self.collectibles:
            if not collectible.collected and player_rect.colliderect(collectible.get_rect()):
                collectible.collected = True
                self.coins += collectible.value
                if "double_coins" in self.active_powerups:
                    self.coins += collectible.value
                self.score += collectible.value * self.combo_multiplier
        
        # Check power-up collisions
        for powerup in self.powerups:
            if not powerup.collected and player_rect.colliderect(powerup.get_rect()):
                powerup.collected = True
                self.activate_powerup(powerup.type, powerup.duration)
    
    def activate_powerup(self, power_type: str, duration: float):
        self.active_powerups[power_type] = duration
        
        if power_type == "shield":
            self.player.invulnerable_time = duration
        elif power_type == "auto_flip":
            # This would be handled in collision detection
            pass
    
    def game_over(self):
        self.state = GameState.GAME_OVER
        self.combo_count = 0
        self.combo_multiplier = 1
    
    def draw_background(self):
        colors = self.get_theme_colors()
        self.screen.fill(colors["bg"])
        
        # Draw theme-specific background elements
        if self.theme == Theme.CITY:
            # Draw city skyline
            for i in range(0, SCREEN_WIDTH, 100):
                height = random.randint(100, 300)
                pygame.draw.rect(self.screen, (30, 30, 60), 
                               (i - int(self.distance * 0.1) % 100, SCREEN_HEIGHT - height, 80, height))
        
        elif self.theme == Theme.CYBERPUNK:
            # Draw neon grid
            for i in range(0, SCREEN_WIDTH, 50):
                pygame.draw.line(self.screen, (100, 0, 100), 
                               (i, 0), (i, SCREEN_HEIGHT), 1)
            for i in range(0, SCREEN_HEIGHT, 50):
                pygame.draw.line(self.screen, (100, 0, 100), 
                               (0, i), (SCREEN_WIDTH, i), 1)
        
        elif self.theme == Theme.JUNGLE:
            # Draw jungle vines
            for i in range(0, SCREEN_WIDTH, 150):
                x = i - int(self.distance * 0.05) % 150
                pygame.draw.line(self.screen, (0, 100, 0), 
                               (x, 0), (x + 20, SCREEN_HEIGHT), 8)
        
        elif self.theme == Theme.SPACE:
            # Draw stars
            for i in range(100):
                x = (i * 123 + int(self.distance * 0.02)) % SCREEN_WIDTH
                y = (i * 456) % SCREEN_HEIGHT
                pygame.draw.circle(self.screen, WHITE, (x, y), 1)
    
    def draw_ui(self):
        # Score
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        # Coins
        coins_text = self.font.render(f"Coins: {self.coins}", True, YELLOW)
        self.screen.blit(coins_text, (10, 50))
        
        # Combo
        if self.combo_count > 0:
            combo_text = self.font.render(f"Combo: {self.combo_count}x (Multiplier: {self.combo_multiplier}x)", True, GREEN)
            self.screen.blit(combo_text, (10, 90))
        
        # Distance
        distance_text = self.small_font.render(f"Distance: {int(self.distance)}m", True, WHITE)
        self.screen.blit(distance_text, (SCREEN_WIDTH - 150, 10))
        
        # Theme
        theme_text = self.small_font.render(f"Theme: {self.theme.value.title()}", True, WHITE)
        self.screen.blit(theme_text, (SCREEN_WIDTH - 150, 35))
        
        # Active power-ups
        y_offset = 130
        for power_type, remaining_time in self.active_powerups.items():
            power_text = self.small_font.render(f"{power_type.replace('_', ' ').title()}: {remaining_time:.1f}s", True, CYAN)
            self.screen.blit(power_text, (10, y_offset))
            y_offset += 25
    
    def draw_menu(self):
        self.screen.fill(BLACK)
        
        # Title
        title_text = self.font.render("GRAVITY FLIP RUNNER", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
        self.screen.blit(title_text, title_rect)
        
        # Instructions
        instructions = [
            "SPACE - Flip Gravity / Start Game",
            "A/D or Arrow Keys - Move",
            "ESC - Pause",
            "",
            "Collect coins and orbs!",
            "Avoid obstacles on both sides!",
            "Chain gravity flips for combo bonuses!"
        ]
        
        y_offset = SCREEN_HEIGHT//2 - 50
        for instruction in instructions:
            if instruction:
                text = self.small_font.render(instruction, True, WHITE)
                text_rect = text.get_rect(center=(SCREEN_WIDTH//2, y_offset))
                self.screen.blit(text, text_rect)
            y_offset += 30
    
    def draw_game_over(self):
        # Draw semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Game Over text
        game_over_text = self.font.render("GAME OVER", True, RED)
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
        self.screen.blit(game_over_text, game_over_rect)
        
        # Final score
        score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(score_text, score_rect)
        
        # Restart instruction
        restart_text = self.small_font.render("Press SPACE or R to restart", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        self.screen.blit(restart_text, restart_rect)
    
    def draw_paused(self):
        # Draw semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Paused text
        paused_text = self.font.render("PAUSED", True, WHITE)
        paused_rect = paused_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(paused_text, paused_rect)
        
        # Resume instruction
        resume_text = self.small_font.render("Press ESC to resume", True, WHITE)
        resume_rect = resume_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        self.screen.blit(resume_text, resume_rect)
    
    def draw(self):
        if self.state == GameState.MENU:
            self.draw_menu()
        
        elif self.state == GameState.PLAYING or self.state == GameState.PAUSED or self.state == GameState.GAME_OVER:
            # Draw background
            self.draw_background()
            
            # Draw game objects
            for platform in self.platforms:
                platform.draw(self.screen, self.camera.rotation)
            
            for obstacle in self.obstacles:
                obstacle.draw(self.screen, self.camera.rotation)
            
            for collectible in self.collectibles:
                collectible.draw(self.screen, self.camera.rotation)
            
            for powerup in self.powerups:
                powerup.draw(self.screen, self.camera.rotation)
            
            # Draw player
            self.player.draw(self.screen, self.camera.rotation)
            
            # Draw UI
            self.draw_ui()
            
            # Draw state-specific overlays
            if self.state == GameState.PAUSED:
                self.draw_paused()
            elif self.state == GameState.GAME_OVER:
                self.draw_game_over()
        
        try:
            pygame.display.flip()
        except pygame.error:
            pass  # Ignore display errors in headless mode
    
    def run_demo(self, duration: float = 10.0):
        """Run a demo simulation of the game for the specified duration"""
        print("🎮 Starting Gravity Flip Runner Demo...")
        print("=" * 50)
        
        self.start_game()
        demo_time = 0
        
        while demo_time < duration and self.state == GameState.PLAYING:
            dt = 1.0 / FPS
            demo_time += dt
            
            # Simulate player input (auto-flip when obstacles approach)
            player_rect = self.player.get_rect()
            for obstacle in self.obstacles:
                if abs(obstacle.pos.x - self.player.pos.x) < 100:
                    if self.player.can_flip:
                        self.player.flip_gravity()
                        self.camera.flip()
                        self.combo_count += 1
                        self.update_combo_multiplier()
                        break
            
            # Simulate horizontal movement
            if demo_time % 2 < 1:
                self.player.move_horizontal(1, dt)
            else:
                self.player.move_horizontal(-1, dt)
            
            self.update(dt)
            
            # Print status every second
            if int(demo_time) != int(demo_time - dt):
                print(f"⏱️  Time: {int(demo_time)}s | Score: {self.score} | Coins: {self.coins} | Combo: {self.combo_count}x | Theme: {self.theme.value}")
        
        print("\n🏁 Demo completed!")
        print(f"📊 Final Stats:")
        print(f"   Score: {self.score}")
        print(f"   Coins: {self.coins}")
        print(f"   Distance: {int(self.distance)}m")
        print(f"   Max Combo: {self.combo_count}")
        print(f"   Active Power-ups: {len(self.active_powerups)}")
        
        return self.score
    
    def run(self):
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
                
                # Apply slow motion effect
                if "slow_motion" in self.active_powerups:
                    dt *= 0.5
                
                self.handle_events()
                self.update(dt)
                self.draw()
        except pygame.error as e:
            print(f"Display error: {e}")
            print("Switching to demo mode...")
            self.run_demo()
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()