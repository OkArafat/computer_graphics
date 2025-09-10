from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import OpenGL.GLUT as GLUT
import random
import time
import math



def _init_rain_pool():
	global raindrops
	raindrops = []
	# Spawn across visible sky footprint
	rng = random.Random(7777)
	count = min(RAIN_POOL_CAP, rain_num_drops)
	for _ in range(count):
		x = rng.uniform(RAIN_X_RANGE[0], RAIN_X_RANGE[1])
		y = rng.uniform(starfield_bounds["y"][1]-0.2, starfield_bounds["y"][1]+0.8)
		z = rng.uniform(RAIN_Z_FAR, -RAIN_Z_NEAR)
		spd = RAIN_SPEED + rng.uniform(-RAIN_SPEED_VAR, RAIN_SPEED_VAR)
		vx = RAIN_DX * (0.6 + rng.random()*0.8)
		vy = -abs(spd)
		vz = 0.0
		length = RAIN_LENGTH * (0.8 + rng.random()*0.6)
		raindrops.append({"pos": [x, y, z], "vel": [vx, vy, vz], "len": length, "alive": True, "splash": 0.0})


def _respawn_drop(r):
	# Recycle above the sky with randomized horizontal position and speed
	rng = random.Random((id(r) ^ int(time.time()*1000)) & 0xffffffff)
	r["pos"][0] = rng.uniform(RAIN_X_RANGE[0], RAIN_X_RANGE[1])
	r["pos"][1] = rng.uniform(starfield_bounds["y"][1]-0.2, starfield_bounds["y"][1]+0.8)
	r["pos"][2] = rng.uniform(RAIN_Z_FAR, -RAIN_Z_NEAR)
	spd = RAIN_SPEED + rng.uniform(-RAIN_SPEED_VAR, RAIN_SPEED_VAR)
	r["vel"][0] = RAIN_DX * (0.6 + rng.random()*0.8)
	r["vel"][1] = -abs(spd)
	r["vel"][2] = 0.0
	r["len"] = RAIN_LENGTH * (0.8 + rng.random()*0.6)
	r["alive"] = True
	r["splash"] = 0.0


def _update_rain(dt):
	global raindrops
	if not raindrops:
		return
	for r in raindrops:
		if not r["alive"]:
			# Splash fade
			r["splash"] -= dt * 6.0
			if r["splash"] <= 0.0:
				_respawn_drop(r)
			continue
		# Integrate motion
		r["pos"][0] += r["vel"][0] * dt
		r["pos"][1] += r["vel"][1] * dt
		r["pos"][2] += r["vel"][2] * dt
		# Ground hit
		if r["pos"][1] <= GROUND_Y + 0.02:
			r["alive"] = False
			r["splash"] = 1.0
			# clamp to ground for splash rendering
			r["pos"][1] = GROUND_Y + 0.02
		# Wrap X outside frustum bounds to keep coverage
		if r["pos"][0] < RAIN_X_RANGE[0]-1.0:
			r["pos"][0] = RAIN_X_RANGE[1]
		elif r["pos"][0] > RAIN_X_RANGE[1]+1.0:
			r["pos"][0] = RAIN_X_RANGE[0]



# Window
width, height = 900, 600

# Lanes (x positions)
LANE_X = [-2.5, 0.0, 2.5]
current_lane_index = 1

# Game state
is_game_over = False
score = 0.0
high_score = 0.0
forward_speed = 12.0  # world units per second
base_forward_speed = 12.0
last_time = None
# Dynamic difficulty
difficulty_factor = 1.0  # grows over time/score
current_difficulty_mode = "EASY"
spawn_cap_per_frame = 1

# Surface flip / camera roll
current_surface = "Floor"  # "Floor" or "Ceiling"
camera_roll_deg = 0.0
target_roll_deg = 0.0
roll_speed_deg_per_sec = 240.0  # degrees per second for easing

# Obstacles: list of dicts {x, z, size}
obstacles = []
spawn_distance_min = 20.0
spawn_distance_max = 40.0
min_gap_z = 4.0  # minimum z gap between obstacles in the same lane (will reduce with difficulty)
min_obstacles_on_screen = 6  # ensure baseline density



# Platforms (floor/ceiling tiles). We keep a modular design so we can extend types easily.
platforms = []  # list[Platform]
platform_spawn_min = 16.0
platform_spawn_max = 30.0
platform_min_gap_z = 6.0

# Player longitudinal offset (forward/back along Z relative to world)
player_z_offset = 0.0
player_z_min = -1.2  # forward (toward -Z)
player_z_max = 1.2   # backward (toward +Z)
player_z_step = 0.6

# Collectibles and FX
collectibles = []  # list of Collectible
orbs_collected = 0
orb_spawn_min_gap = 10.0
orb_spawn_max_gap = 24.0
car_fire_particles = []  # list of particles: {pos:[x,y,z], vel:[vx,vy,vz], life:float, color:(r,g,b), size:float}
car_fire_max_life = 0.9

# Bullets and wall debris
bullets = []  # list of dicts {lane:int, side:str, z:float, speed:float, alive:bool}
bullet_speed = 28.0
bullet_cooldown = 0.20
_last_bullet_time = 0.0
wall_debris = []  # list of dicts {pos:[x,y,z], vel:[vx,vy,vz], life:float, size:float}
wall_debris_max_life = 0.8

# Cheat mode
cheat_active = False
cheat_until_ts = 0.0

# Abilities and Power-ups
invisibility_active = False
invisibility_until_ts = 0.0
auto_flip_safety_active = False
auto_flip_until_ts = 0.0
shield_active = False
shield_until_ts = 0.0
inverted_controls_active = False
inverted_controls_until_ts = 0.0
random_flip_active = False
random_flip_until_ts = 0.0
random_flip_timer = 0.0

# Combo & Streak System
wall_break_streak = 0
streak_bonus_threshold = 5
last_wall_break_time = 0.0
combo_display_time = 0.0

# Easy Path Mode
easy_path_active = False
easy_path_until_ts = 0.0
easy_path_cost = 20

# Revive system
revive_available = False
waiting_for_revive_choice = False

# Theme system
current_theme = None  # 'city' | 'jungle' | 'space'
theme_selection_active = False
selection_window_id = None
main_window_id = None
selection_window_w = 1200
selection_window_h = 500

# Game state management
game_state = "welcome"  # "welcome" -> "theme_selection" -> "tutorial" -> "playing"
tutorial_step = 0
tutorial_max_steps = 6
tutorial_timer = 0.0

# Occasion system (sky/atmosphere overlays; independent of base theme)
# None | 'night' | 'day' | 'night_rain' | 'day_rain' | 'ufo'
current_occasion = None

# Celestials (Sun, Moon, Stars, Comets)
# Colors from hex aesthetic palette
def _hex_to_rgb(hex_str):
	"""Convert '#RRGGBB' to tuple of floats 0..1."""
	hex_str = hex_str.strip().lstrip('#')
	r = int(hex_str[0:2], 16) / 255.0
	g = int(hex_str[2:4], 16) / 255.0
	b = int(hex_str[4:6], 16) / 255.0
	return (r, g, b)

# Base palette
_SUN_COLOR = _hex_to_rgb('#FFD93D')
_MOON_COLOR = _hex_to_rgb('#CFCFCF')
_STAR_COLOR = _hex_to_rgb('#E0FFFF')
_COMET_TAIL_COLOR = _hex_to_rgb('#FF6F61')

# Celestial state
celestial_fade = 0.0			# 0..1 visible intensity based on theme
celestial_target_fade = 0.0
celestial_fade_speed = 1.6	# per second

stars = []					# list of dicts: {pos:(x,y,z), size:float, phase:float}
num_stars_base = 140
num_stars_space = 420
# Unified sky ranges (cover full frustum)
SKY_X_RANGE = (-18.0, 18.0)
SKY_Y_RANGE = (2.5, 8.0)
SKY_Z_RANGE = (-40.0, -220.0)
starfield_bounds = {
	"x": SKY_X_RANGE,
	"y": SKY_Y_RANGE,
	"z": SKY_Z_RANGE,
}
twinkle_speed = 1.6
twinkle_multiplier = 1.0

comets = []					# list of dicts: {pos:[x,y,z], vel:[vx,vy,vz], tail:[{pos, life}], life:float}
comet_spawn_timer = 0.0
comet_spawn_cooldown = (8.0, 16.0)
comet_spawn_next = 10.0
comet_head_radius = 0.15
comet_tail_max = 40

# Active palette (can be overridden by occasion themes)
celestial_palette = {
	"sun": _SUN_COLOR,
	"moon": _MOON_COLOR,
	"stars": _STAR_COLOR,
	"comet_tail": _COMET_TAIL_COLOR,
}

# Clouds/Rain/UFO state
clouds = []  # list of dicts {pos:[x,y,z], size:float, speed:float, alpha:float}
raindrops = []  # list of dicts {pos:[x,y,z], vel:[vx,vy,vz], life:float}
ufos = []  # list of dicts {pos:[x,y,z], vel:[vx,vy,vz], wobble:float, phase:float}
rain_spawn_accum = 0.0
ufo_spawn_timer = 0.0
ufo_spawn_next = 12.0

# Rain physics (3D-adapted from Arafat's 2D implementation)
NUM_DROPS_DEFAULT = 1200
RAIN_LENGTH = 0.65
RAIN_SPEED = 14.0
RAIN_SPEED_VAR = 6.0
RAIN_DX = -1.2  # diagonal wind drift along X
GROUND_Y = -1.0  # ground plane matches ground quad
RAIN_POOL_CAP = 2000
rain_num_drops = NUM_DROPS_DEFAULT
RAIN_X_RANGE = (-16.0, 16.0)
RAIN_Z_NEAR = 6.0
RAIN_Z_FAR = -180.0


def _theme_celestial_flags():
	"""Decide which celestial elements should be visible for the current theme.
	This is intentionally simple and extendable. Add more themes/occasions later.
	"""
	# Built-in main themes
	is_space = (current_theme == 'space')
	is_city = (current_theme == 'city')
	is_jungle = (current_theme == 'jungle')
	flags = {
		# Sun shows only in city; Jungle uses moon instead; Space uses stars
		"sun": bool(is_city and not is_space),
		"moon": bool(is_jungle and not is_space),
		"stars": bool(is_space),
		"comets": bool(is_space),
		"dense_starfield": bool(is_space),
		"sun_color": _SUN_COLOR,
		"moon_color": _MOON_COLOR,
		"star_color": _STAR_COLOR,
		"comet_tail_color": _COMET_TAIL_COLOR,
		"twinkle_mul": 1.0,
		"comet_rate": "normal",  # normal|dense|rare
		# Space should not allow rain
		"allow_rain": (current_theme != 'space'),
	}

	# Occasion overlays (do NOT change ground). Merge on top of base flags
	if current_occasion == 'day':
		flags.update({"sun": True, "moon": False, "stars": False, "comets": False, "dense_starfield": False, "twinkle_mul": 0.8})
	elif current_occasion == 'night':
		flags.update({"sun": False, "moon": True, "stars": True, "comets": False, "dense_starfield": False, "twinkle_mul": 1.0})
	elif current_occasion == 'night_rain':
		flags.update({"sun": False, "moon": True, "stars": True, "comets": False, "dense_starfield": False, "twinkle_mul": 1.0})
	elif current_occasion == 'day_rain':
		flags.update({"sun": True, "moon": False, "stars": False, "comets": False, "dense_starfield": False, "twinkle_mul": 0.8})
	elif current_occasion == 'ufo':
		# Keep base theme; add UFO accompaniment; enable stars unless sun is showing
		is_daytime = flags.get("sun", False)
		flags.update({"stars": flags["stars"] or (not is_daytime), "comets": flags["comets"], "dense_starfield": flags["dense_starfield"] or is_space, "twinkle_mul": 1.2 if not is_daytime else 0.8})

	return flags


def _regen_stars(dense=False):
	global stars
	stars = []
	count = num_stars_space if dense else num_stars_base
	rng = random.Random(1337)
	for _ in range(count):
		x = rng.uniform(SKY_X_RANGE[0], SKY_X_RANGE[1])
		y = rng.uniform(SKY_Y_RANGE[0], SKY_Y_RANGE[1])
		z = rng.uniform(SKY_Z_RANGE[0], SKY_Z_RANGE[1])
		size = rng.uniform(0.008, 0.020) * (1.6 if dense else 1.0)
		phase = rng.uniform(0.0, 6.28318)
		stars.append({"pos": (x, y, z), "size": size, "phase": phase})


def init_celestials_for_theme():
	"""Initialize starfield density, fade target, and comet timers for current theme."""
	global celestial_target_fade, comet_spawn_timer, comet_spawn_next, comets, celestial_palette, twinkle_multiplier, _SUN_COLOR, _MOON_COLOR, _STAR_COLOR, _COMET_TAIL_COLOR, clouds, raindrops, ufos, rain_spawn_accum, ufo_spawn_timer, ufo_spawn_next
	flags = _theme_celestial_flags()
	_regen_stars(dense=flags["dense_starfield"])
	comets = []
	comet_spawn_timer = 0.0
	# Twinkle multiplier
	twinkle_multiplier = max(0.2, float(flags.get("twinkle_mul", 1.0)))
	# Palette overrides
	celestial_palette = {
		"sun": flags.get("sun_color", _SUN_COLOR),
		"moon": flags.get("moon_color", _MOON_COLOR),
		"stars": flags.get("star_color", _STAR_COLOR),
		"comet_tail": flags.get("comet_tail_color", _COMET_TAIL_COLOR),
	}
	# Comet spawn rate
	if flags["dense_starfield"] or flags.get("comet_rate") == "dense":
		min_cd, max_cd = (3.0, 7.0)
	elif flags.get("comet_rate") == "rare":
		min_cd, max_cd = (10.0, 18.0)
	else:
		min_cd, max_cd = comet_spawn_cooldown
	comet_spawn_next = random.uniform(min_cd, max_cd)
	celestial_target_fade = 1.0 if (flags["sun"] or flags["moon"] or flags["stars"] or flags["comets"]) else 0.0

	# Initialize clouds/rain/UFO state per occasion
	clouds = []
	raindrops = []
	rain_spawn_accum = 0.0
	ufos = []
	ufo_spawn_timer = 0.0
	ufo_spawn_next = random.uniform(8.0, 14.0)
	if current_occasion in ('day', 'day_rain'):
		# seed a few clouds
		rng = random.Random(4242)
		for _ in range(24):
			x = rng.uniform(starfield_bounds["x"][0], starfield_bounds["x"][1])
			y = rng.uniform(3.6, 6.5)
			z = rng.uniform(-70.0, -130.0)
			sz = rng.uniform(0.8, 1.8)
			spd = rng.uniform(0.25, 0.55)
			clouds.append({"pos": [x, y, z], "size": sz, "speed": spd, "alpha": 0.6, "phase": rng.uniform(0.0, 6.28)})
	if current_occasion == 'ufo':
		# seed some ufos initially
		rng = random.Random(5252)
		for _ in range(10):
			x = rng.uniform(SKY_X_RANGE[0], SKY_X_RANGE[1])
			y = rng.uniform(3.0, 6.8)
			z = rng.uniform(SKY_Z_RANGE[0]*0.6, SKY_Z_RANGE[1]*0.6)
			vx = rng.uniform(-2.5, 2.5)
			if abs(vx) < 0.8:
				vx = 1.2 if (rng.random()<0.5) else -1.2
			ufos.append({"pos": [x, y, z], "vel": [vx, 0.0, 0.0], "wobble": 0.0, "phase": rng.uniform(0.0, 6.28)})
	# Initialize rain pool if raining and theme allows rain
	if current_occasion in ('day_rain', 'night_rain') and flags.get("allow_rain", True):
		_init_rain_pool()


def update_celestials(dt, now):
	"""Update fade, twinkle, and comet motion/spawn each frame."""
	global celestial_fade, comet_spawn_timer, comet_spawn_next, comets
	# Fade toward target
	if celestial_fade < celestial_target_fade:
		celestial_fade = min(celestial_target_fade, celestial_fade + celestial_fade_speed * dt)
	elif celestial_fade > celestial_target_fade:
		celestial_fade = max(celestial_target_fade, celestial_fade - celestial_fade_speed * dt)
	# Twinkle
	if stars:
		for s in stars:
			s["phase"] += (twinkle_speed * twinkle_multiplier) * dt
	# Comets
	flags = _theme_celestial_flags()
	# Move and age tails
	if comets:
		for c in comets:
			c["pos"][0] += c["vel"][0] * dt
			c["pos"][1] += c["vel"][1] * dt
			c["pos"][2] += c["vel"][2] * dt
			# grow tail
			c.setdefault("tail", []).append({"pos": tuple(c["pos"]), "life": 1.0})
			for seg in c["tail"]:
				seg["life"] -= dt * 1.8
		# cull finished
		alive = []
		for c in comets:
			px, py, pz = c["pos"]
			if px < starfield_bounds["x"][0]-2 or px > starfield_bounds["x"][1]+2 or \
			   py < 1.0 or py > starfield_bounds["y"][1]+2 or \
			   pz > -10.0 or pz < starfield_bounds["z"][1]-20:
				continue
			c["tail"] = [seg for seg in c.get("tail", []) if seg["life"] > 0]
			alive.append(c)
		comets = alive
	# Spawn new comets
	comet_spawn_timer += dt
	if flags["comets"] and comet_spawn_timer >= comet_spawn_next:
		comet_spawn_timer = 0.0
		min_cd, max_cd = (2.0, 5.0) if flags["dense_starfield"] else comet_spawn_cooldown
		comet_spawn_next = random.uniform(min_cd, max_cd)
		# Spawn from wider sky: random side and altitude within sky ranges
		from_left = (random.random() < 0.5)
		start_x = SKY_X_RANGE[0]-2.0 if from_left else SKY_X_RANGE[1]+2.0
		start_y = random.uniform(SKY_Y_RANGE[1]-1.0, SKY_Y_RANGE[1])
		start_z = random.uniform(SKY_Z_RANGE[0]*0.7, SKY_Z_RANGE[1]*0.7)
		speed = random.uniform(8.0, 14.0) * (1.4 if flags["dense_starfield"] else 1.0)
		vx = speed * (0.6 if from_left else -0.6)
		vy = -speed * 0.35
		vz = speed * 0.15
		comets.append({"pos": [start_x, start_y, start_z], "vel": [vx, vy, vz], "tail": [], "life": 1.0})

	# Rain particles for rain occasions
	flags_now = _theme_celestial_flags()
	if current_occasion in ('day_rain', 'night_rain') and flags_now.get("allow_rain", True):
		_update_rain(dt)

	# UFO spawns for UFO occasion
	if current_occasion == 'ufo':
		_update_ufos(dt)

	# Clouds drift for day/day_rain
	if current_occasion in ('day', 'day_rain') and clouds:
		for c in clouds:
			c["pos"][0] += c.get("speed", 0.4) * dt
			c["phase"] = c.get("phase", 0.0) + 0.5 * dt
			if c["pos"][0] > SKY_X_RANGE[1] + 1.0:
				c["pos"][0] = SKY_X_RANGE[0] - 1.0


def _spawn_and_update_rain(dt):
	global raindrops, rain_spawn_accum
	# Spawn rate scales with width of sky
	rain_spawn_accum += dt
	spawn_rate = 80.0  # drops per second baseline
	to_spawn = int(rain_spawn_accum * spawn_rate)
	if to_spawn > 0:
		rain_spawn_accum -= to_spawn / spawn_rate
		rng = random.Random(int(time.time()*1000) & 0xffffffff)
		for _ in range(to_spawn):
			x = rng.uniform(starfield_bounds["x"][0], starfield_bounds["x"][1])
			y = rng.uniform(starfield_bounds["y"][1]-0.2, starfield_bounds["y"][1]+0.5)
			z = rng.uniform(-70.0, -130.0)
			vx = rng.uniform(-0.5, 0.2)
			vy = -rng.uniform(10.0, 16.0)
			vz = 0.0
			raindrops.append({"pos": [x, y, z], "vel": [vx, vy, vz], "life": 2.5})
	# Integrate
	for r in raindrops:
		r["pos"][0] += r["vel"][0] * dt
		r["pos"][1] += r["vel"][1] * dt
		r["pos"][2] += r["vel"][2] * dt
		r["life"] -= dt
	# Cull
	raindrops = [r for r in raindrops if r["life"] > 0 and r["pos"][1] > 1.2]


def _update_ufos(dt):
	global ufos, ufo_spawn_timer, ufo_spawn_next
	ufo_spawn_timer += dt
	if ufo_spawn_timer >= ufo_spawn_next:
		ufo_spawn_timer = 0.0
		ufo_spawn_next = random.uniform(6.0, 12.0)
		# Spawn from left or right randomly
		from_left = (random.random() < 0.5)
		x = starfield_bounds["x"][0]-1.5 if from_left else starfield_bounds["x"][1]+1.5
		y = random.uniform(3.2, 6.2)
		z = random.uniform(-75.0, -110.0)
		s = random.uniform(1.6, 2.4)
		vx = s * (1.0 if from_left else -1.0)
		vy = 0.0
		vz = 0.0
		ufos.append({"pos": [x, y, z], "vel": [vx, vy, vz], "wobble": 0.0, "phase": random.uniform(0.0, 6.28)})
	# Move and cull
	for u in ufos:
		u["pos"][0] += u["vel"][0] * dt
		u["phase"] += dt
	# keep on screen bounds
	ufos = [u for u in ufos if starfield_bounds["x"][0]-2.0 <= u["pos"][0] <= starfield_bounds["x"][1]+2.0]

def get_theme_def():
	# Return dict of theme parameters
	if current_theme == 'city':
		return {
			"ground_color": (0.12, 0.12, 0.12),
			"lane_color": (0.9, 0.9, 0.3),
			"obstacle_weights": [
				("car", 0.30), ("barrier", 0.20), ("cone", 0.20), ("bus", 0.15), ("cube", 0.15)
			],
		}
	elif current_theme == 'jungle':
		return {
			"ground_color": (0.09, 0.12, 0.09),
			"lane_color": (0.6, 0.8, 0.3),
			"obstacle_weights": [
				("stone", 0.35), ("pillar", 0.25), ("log", 0.20), ("trap", 0.15), ("cube", 0.05)
			],
		}
	elif current_theme == 'space':
		return {
			"ground_color": (0.08, 0.09, 0.12),
			"lane_color": (0.5, 0.8, 1.0),
			"obstacle_weights": [
				("drone", 0.30), ("ring", 0.25), ("gate", 0.25), ("ball", 0.10), ("cube", 0.10)
			],
		}
	# default
	return {
		"ground_color": (0.1, 0.12, 0.16),
		"lane_color": (0.8, 0.8, 0.2),
		"obstacle_weights": [("cube", 1.0)],
	}

def draw_welcome_screen():
	"""Draw the welcome screen with title and prompt."""
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glLoadIdentity()
	
	# Dark background
	glClearColor(0.05, 0.05, 0.08, 1.0)
	
	# Title - large and centered
	title_x = width * 0.5 - 200
	title_y = height * 0.7
	draw_text(title_x, title_y, "GRAVITY FLIP RUNNER", font=GLUT.GLUT_BITMAP_TIMES_ROMAN_24, color=(0.9, 0.9, 1.0))
	
	# Subtitle
	subtitle_x = width * 0.5 - 180
	subtitle_y = height * 0.6
	draw_text(subtitle_x, subtitle_y, "Experience the Ultimate Dual-Surface Adventure", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=(0.7, 0.8, 0.9))
	
	# Animated prompt
	phase = (time.time() * 2.0) % 2.0
	alpha = 0.5 + 0.5 * abs(phase - 1.0)
	prompt_color = (alpha, alpha * 0.9, 1.0)
	prompt_x = width * 0.5 - 100
	prompt_y = height * 0.35
	draw_text(prompt_x, prompt_y, "Press ENTER to Continue", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=prompt_color)
	
	# Version info
	version_x = width * 0.5 - 50
	version_y = height * 0.1
	draw_text(version_x, version_y, "v2.0 Enhanced Edition", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.5, 0.5, 0.6))
	
	glutSwapBuffers()


def draw_theme_selection_screen():
	"""Draw the theme selection screen."""
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glLoadIdentity()
	
	# Title
	title_x = width * 0.5 - 120
	title_y = height * 0.85
	draw_text(title_x, title_y, "SELECT YOUR THEME", font=GLUT.GLUT_BITMAP_TIMES_ROMAN_24, color=(1.0, 1.0, 1.0))
	
	# Theme options with descriptions
	option_y = height * 0.7
	spacing = 80
	
	# City theme
	draw_text(100, option_y, "1. CITY THEME", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=(0.9, 0.8, 0.3))
	draw_text(120, option_y - 25, "Navigate through urban obstacles:", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.8, 0.8, 0.8))
	draw_text(120, option_y - 40, "Cars, buses, barriers, traffic cones", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.7, 0.7, 0.7))
	
	# Jungle theme
	option_y -= spacing
	draw_text(100, option_y, "2. JUNGLE THEME", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=(0.5, 0.9, 0.4))
	draw_text(120, option_y - 25, "Explore ancient ruins with:", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.8, 0.8, 0.8))
	draw_text(120, option_y - 40, "Stone blocks, pillars, fallen logs", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.7, 0.7, 0.7))
	
	# Space theme
	option_y -= spacing
	draw_text(100, option_y, "3. SPACE THEME", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=(0.5, 0.8, 1.0))
	draw_text(120, option_y - 25, "Journey through space stations:", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.8, 0.8, 0.8))
	draw_text(120, option_y - 40, "Drones, energy rings, force gates", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.7, 0.7, 0.7))
	
	# Prompt
	prompt_x = width * 0.5 - 120
	prompt_y = height * 0.15
	draw_text(prompt_x, prompt_y, "Press 1, 2, or 3 to select", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=(1.0, 1.0, 0.8))
	
	glutSwapBuffers()


def get_tutorial_content(step):
	"""Get tutorial content for each step."""
	contents = [
		{
			"title": "GRAVITY FLIP MECHANIC",
			"text": [
				"Press SPACEBAR to flip between floor and ceiling",
				"Camera smoothly rotates 180° during flips",
				"Brief invincibility protects you during transitions",
				"Master this to navigate dual-layer obstacles!"
			],
			"controls": "SPACEBAR - Flip Gravity"
		},
		{
			"title": "MOVEMENT CONTROLS",
			"text": [
				"Use ARROW KEYS or A/D to move between lanes",
				"W/S keys move you forward/backward on the track",
				"Controls invert when you're on the ceiling",
				"Practice smooth lane switching for survival!"
			],
			"controls": "ARROWS/A,D - Change lanes, W/S - Move along track"
		},
		{
			"title": "OBSTACLES & DANGERS",
			"text": [
				"Moving Spikes: Slide across lanes horizontally",
				"Rotating Blades: Spin continuously - time your passage",
				"Electric Walls: Can be destroyed with bullets",
				"Breakable Platforms: Crack and fall after stepping"
			],
			"controls": "F/MOUSE - Fire bullets to break walls"
		},
		{
			"title": "COLLECTIBLES & ORBS",
			"text": [
				"Golden Orbs: Collect for abilities and power-ups",
				"Trap Coins: Red coins that cause explosions",
				"Use orbs to purchase helpful abilities",
				"Orbs also allow revival after death"
			],
			"controls": "Collect orbs by touching them"
		},
		{
			"title": "POWER-UPS & ABILITIES",
			"text": [
				"C - Cheat Mode (10 orbs): 3s invincibility",
				"I - Invisibility (5 orbs): Pass through obstacles",
				"H - Shield (10 orbs): Collision immunity",
				"T - Auto-Flip (8 orbs): Automatic danger avoidance"
			],
			"controls": "Press keys when you have enough orbs"
		},
		{
			"title": "ADVANCED FEATURES",
			"text": [
				"E - Easy Path (20 orbs): 3s obstacle-free mode",
				"Combo System: 5 wall breaks = +10 orbs bonus",
				"Weather: Keys 5-9 change seasons and atmosphere",
				"Revive: Use 15 orbs to continue after death"
			],
			"controls": "Master these for high scores!"
		}
	]
	return contents[step] if step < len(contents) else contents[-1]


def draw_tutorial_screen():
	"""Draw the tutorial/tour screen."""
	global tutorial_timer
	tutorial_timer += 0.016  # Assume 60fps
	
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glLoadIdentity()
	
	content = get_tutorial_content(tutorial_step)
	
	# Title
	title_x = width * 0.5 - len(content["title"]) * 6
	title_y = height * 0.9
	draw_text(title_x, title_y, content["title"], font=GLUT.GLUT_BITMAP_TIMES_ROMAN_24, color=(1.0, 0.9, 0.3))
	
	# Step indicator
	step_text = f"Step {tutorial_step + 1} of {tutorial_max_steps}"
	step_x = width * 0.5 - len(step_text) * 4
	step_y = height * 0.85
	draw_text(step_x, step_y, step_text, font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.7, 0.7, 0.7))
	
	# Content text
	text_y = height * 0.7
	for line in content["text"]:
		line_x = 80
		draw_text(line_x, text_y, f"• {line}", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.9, 0.9, 0.9))
		text_y -= 25
	
	# Controls highlight
	controls_y = height * 0.4
	draw_text(80, controls_y, "CONTROLS:", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=(0.3, 1.0, 0.3))
	draw_text(80, controls_y - 30, content["controls"], font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.8, 1.0, 0.8))
	
	# Navigation
	nav_y = height * 0.15
	if tutorial_step > 0:
		draw_text(80, nav_y, "← BACKSPACE - Previous", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.8, 0.8, 1.0))
	
	if tutorial_step < tutorial_max_steps - 1:
		draw_text(width - 200, nav_y, "SPACE - Next →", font=GLUT.GLUT_BITMAP_HELVETICA_12, color=(0.8, 0.8, 1.0))
	else:
		# Animated "Start Game" prompt
		phase = (tutorial_timer * 3.0) % 2.0
		alpha = 0.6 + 0.4 * abs(phase - 1.0)
		start_color = (alpha, 1.0, alpha)
		draw_text(width - 250, nav_y, "ENTER - Start Game!", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=start_color)
	
	glutSwapBuffers()


def advance_game_state():
	"""Advance to the next game state."""
	global game_state, theme_selection_active, tutorial_step
	
	if game_state == "welcome":
		game_state = "theme_selection"
	elif game_state == "theme_selection":
		game_state = "tutorial"
		tutorial_step = 0
	elif game_state == "tutorial":
		if tutorial_step < tutorial_max_steps - 1:
			tutorial_step += 1
		else:
			game_state = "playing"
			# Initialize the game
			reset_game()


def go_back_tutorial():
	"""Go back in tutorial or game states."""
	global tutorial_step, game_state
	
	if game_state == "tutorial" and tutorial_step > 0:
		tutorial_step -= 1


def choose_by_weights(pairs):
	# pairs: list of (value, weight)
	total = sum(w for _, w in pairs)
	r = random.random() * max(1e-6, total)
	acc = 0.0
	for v, w in pairs:
		acc += w
		if r <= acc:
			return v
	return pairs[-1][0]


def fire_bullet():
	global _last_bullet_time, bullets
	now_ts = time.time()
	if now_ts - _last_bullet_time >= bullet_cooldown:
		_last_bullet_time = now_ts
		bullets.append({
			"lane": current_lane_index,
			"side": current_surface,
			"z": player_z_offset - 0.2,
			"speed": bullet_speed,
			"alive": True,
		})


def activate_ability(ability_type):
	global invisibility_active, invisibility_until_ts, auto_flip_safety_active, auto_flip_until_ts, shield_active, shield_until_ts, inverted_controls_active, inverted_controls_until_ts, random_flip_active, random_flip_until_ts, orbs_collected, cheat_active, cheat_until_ts
	
	if ability_type == "invisibility" and orbs_collected >= 5:
		orbs_collected -= 5
		invisibility_active = True
		invisibility_until_ts = time.time() + 3.0
		
	elif ability_type == "auto_flip_safety" and orbs_collected >= 8:
		orbs_collected -= 8
		auto_flip_safety_active = True
		auto_flip_until_ts = time.time() + 5.0
		
	elif ability_type == "shield" and orbs_collected >= 10:
		orbs_collected -= 10
		shield_active = True
		shield_until_ts = time.time() + 4.0
		
	elif ability_type == "inverted_controls" and orbs_collected >= 3:
		orbs_collected -= 3
		inverted_controls_active = True
		inverted_controls_until_ts = time.time() + 8.0
		
	elif ability_type == "random_flip" and orbs_collected >= 4:
		orbs_collected -= 4
		random_flip_active = True
		random_flip_until_ts = time.time() + 6.0


def activate_easy_path():
	global easy_path_active, easy_path_until_ts, orbs_collected
	if orbs_collected >= easy_path_cost:
		orbs_collected -= easy_path_cost
		easy_path_active = True
		easy_path_until_ts = time.time() + 3.0
		return True
	return False


def update_abilities(dt, now):
	global invisibility_active, auto_flip_safety_active, shield_active, inverted_controls_active, random_flip_active, easy_path_active, random_flip_timer
	
	# Update ability timers
	if invisibility_active and now >= invisibility_until_ts:
		invisibility_active = False
	if auto_flip_safety_active and now >= auto_flip_until_ts:
		auto_flip_safety_active = False
	if shield_active and now >= shield_until_ts:
		shield_active = False
	if inverted_controls_active and now >= inverted_controls_until_ts:
		inverted_controls_active = False
	if random_flip_active and now >= random_flip_until_ts:
		random_flip_active = False
	if easy_path_active and now >= easy_path_until_ts:
		easy_path_active = False
	
	# Random flip mechanic
	if random_flip_active:
		random_flip_timer += dt
		if random_flip_timer >= 2.0:  # Random flip every 2 seconds
			random_flip_timer = 0.0
			trigger_gravity_flip()


def trigger_gravity_flip():
	global current_surface, target_roll_deg
	if current_surface == "Floor":
		current_surface = "Ceiling"
		target_roll_deg = 180.0
	else:
		current_surface = "Floor"
		target_roll_deg = 0.0


def check_auto_flip_safety():
	global current_surface, target_roll_deg
	if not auto_flip_safety_active:
		return
	
	# Check for incoming obstacles on current surface within danger zone
	player_x = LANE_X[current_lane_index]
	danger_distance = 3.0
	
	for obs in obstacles:
		if obs.get("side", "Floor") == current_surface:
			if abs(obs["x"] - player_x) < 0.5 and -danger_distance <= obs["z"] <= 0:
				# Danger detected, auto-flip
				trigger_gravity_flip()
				return


def update_combo_streak(dt):
	global combo_display_time, last_wall_break_time
	current_time = time.time()
	
	# Reset streak if too much time passed since last wall break
	if current_time - last_wall_break_time > 3.0:
		global wall_break_streak
		wall_break_streak = 0
	
	# Update combo display timer
	if combo_display_time > 0:
		combo_display_time -= dt


def award_streak_bonus():
	global wall_break_streak, score, orbs_collected, combo_display_time, last_wall_break_time
	wall_break_streak += 1
	last_wall_break_time = time.time()
	
	if wall_break_streak >= streak_bonus_threshold:
		bonus_coins = 10
		orbs_collected += bonus_coins
		score += 50  # Bonus score too
		combo_display_time = 2.0  # Show combo message for 2 seconds
		wall_break_streak = 0  # Reset after bonus


def spawn_wall_debris(x, y, z):
	# Spawn small chunk particles when a wall breaks
	rng = random.Random(hash((int(time.time()*1000), int(x*10), int(z*10))) & 0xffffffff)
	for _ in range(14):
		vx = rng.uniform(-1.2, 1.2)
		vz = rng.uniform(-0.8, 0.8)
		vy = rng.uniform(1.2, 2.4) * (1.0 if current_surface == "Ceiling" else -1.0)
		size = rng.uniform(0.08, 0.16)
		wall_debris.append({
			"pos": [x + rng.uniform(-0.3, 0.3), y + (0.2 if current_surface == "Floor" else -0.2), z + rng.uniform(-0.2, 0.2)],
			"vel": [vx, vy, vz],
			"life": wall_debris_max_life,
			"size": size,
		})


def update_dynamic_obstacles(dt):
	"""Update moving spikes, rotating blades, and other dynamic obstacles."""
	for obs in obstacles:
		otype = obs.get("type")
		
		# Moving spikes
		if otype == "moving_spike":
			if "move_phase" not in obs:
				obs["move_phase"] = 0.0
			obs["move_phase"] += dt * obs.get("move_speed", 2.0)
			obs["x"] = obs["base_x"] + obs.get("move_range", 1.0) * math.sin(obs["move_phase"])
		
		# Rotating blades
		elif otype == "rotating_blade":
			if "rotation" not in obs:
				obs["rotation"] = 0.0
			obs["rotation"] += dt * obs.get("rotate_speed", 180.0)  # degrees per second
			obs["rotation"] %= 360.0
		
		# Electric walls with energy pulsing
		elif otype == "electric_wall":
			if "pulse_phase" not in obs:
				obs["pulse_phase"] = 0.0
			obs["pulse_phase"] += dt * 3.0
			obs["energy"] = 0.5 + 0.5 * math.sin(obs["pulse_phase"])


def create_enhanced_obstacle(lane, target_z, side, otype):
	"""Create obstacles with enhanced properties for dual-layer gameplay."""
	obs = {"x": LANE_X[lane], "z": target_z, "size": 1.5, "side": side, "type": otype}
	
	if otype == "moving_spike":
		obs["base_x"] = LANE_X[lane]
		obs["move_range"] = random.uniform(0.8, 1.5)
		obs["move_speed"] = random.uniform(1.5, 3.0)
		obs["move_phase"] = random.uniform(0, 6.28)
		obs["spike_count"] = random.randint(3, 6)
		
	elif otype == "rotating_blade":
		obs["rotation"] = random.uniform(0, 360)
		obs["rotate_speed"] = random.uniform(120, 300)
		obs["blade_radius"] = random.uniform(0.8, 1.2)
		obs["blade_count"] = random.randint(3, 5)
		
	elif otype == "electric_wall":
		obs["pulse_phase"] = random.uniform(0, 6.28)
		obs["energy"] = 1.0
		obs["width"] = random.uniform(1.6, 2.0)
		obs["height"] = random.uniform(1.0, 1.4)
		obs["thickness"] = 0.1
		
	return obs


# --- Selection UI helpers ---
def _sel_draw_gradient_bg(w, h, top_color, bottom_color):
	glDisable(GL_DEPTH_TEST)
	glMatrixMode(GL_PROJECTION)
	glPushMatrix()
	glLoadIdentity()
	gluOrtho2D(0, w, 0, h)
	glMatrixMode(GL_MODELVIEW)
	glPushMatrix()
	glLoadIdentity()
	glBegin(GL_QUADS)
	glColor3f(*top_color)
	glVertex2f(0, h)
	glVertex2f(w, h)
	glColor3f(*bottom_color)
	glVertex2f(w, 0)
	glVertex2f(0, 0)
	glEnd()
	glPopMatrix()
	glMatrixMode(GL_PROJECTION)
	glPopMatrix()
	glMatrixMode(GL_MODELVIEW)
	glEnable(GL_DEPTH_TEST)


def _sel_draw_card(cx, cy, cw, ch, title, subtitle, base_color, glow_phase):
	# Shadow
	glDisable(GL_DEPTH_TEST)
	glMatrixMode(GL_PROJECTION)
	glPushMatrix()
	glLoadIdentity()
	gluOrtho2D(0, 1, 0, 1)
	glMatrixMode(GL_MODELVIEW)
	glPushMatrix()
	glLoadIdentity()

	# Convert to NDC fractional space (use 0..1)
	x0 = cx - cw * 0.5
	y0 = cy - ch * 0.5
	x1 = cx + cw * 0.5
	y1 = cy + ch * 0.5

	# Shadow rect (slightly offset)
	glColor3f(0.06, 0.06, 0.08)
	glBegin(GL_QUADS)
	glVertex2f(x0 + 0.01, y0 - 0.01)
	glVertex2f(x1 + 0.01, y0 - 0.01)
	glVertex2f(x1 + 0.01, y1 - 0.01)
	glVertex2f(x0 + 0.01, y1 - 0.01)
	glEnd()

	# Card fill
	glColor3f(base_color[0] * 0.2 + 0.08, base_color[1] * 0.2 + 0.08, base_color[2] * 0.2 + 0.10)
	glBegin(GL_QUADS)
	glVertex2f(x0, y0)
	glVertex2f(x1, y0)
	glVertex2f(x1, y1)
	glVertex2f(x0, y1)
	glEnd()

	# Animated border glow
	glLineWidth(3.0)
	glColor3f(base_color[0] * (0.6 + 0.4 * glow_phase), base_color[1] * (0.6 + 0.4 * glow_phase), base_color[2] * (0.6 + 0.4 * glow_phase))
	glBegin(GL_LINE_LOOP)
	glVertex2f(x0, y0)
	glVertex2f(x1, y0)
	glVertex2f(x1, y1)
	glVertex2f(x0, y1)
	glEnd()

	# Title/subtitle using pixel-space helper
	# Map fractional to pixel coords for draw_text_2d
	glPopMatrix()
	glMatrixMode(GL_PROJECTION)
	glPopMatrix()
	glMatrixMode(GL_MODELVIEW)

	# Use current selection window size
	global selection_window_w, selection_window_h
	win_w, win_h = selection_window_w, selection_window_h
	tx = int(cx * win_w - cw * 0.5 * win_w) + 18
	ty = int(cy * win_h + ch * 0.5 * win_h) - 38
	draw_text_2d(tx, ty, title)
	draw_text_2d(tx, ty - 22, subtitle)
	glEnable(GL_DEPTH_TEST)

class Platform:
	def __init__(self, lane_index, side, z_center, length=3.0, width=2.4, thickness=0.2, color=(0.18, 0.18, 0.22)):
		self.lane_index = lane_index  # 0..2
		self.side = side  # "Floor" or "Ceiling"
		self.z = z_center
		self.length = length
		self.width = width
		self.thickness = thickness
		self.color = color
		self.collider_enabled = True

	def aabb(self):
		half_l = self.length * 0.5
		return (LANE_X[self.lane_index] - self.width * 0.5,
				LANE_X[self.lane_index] + self.width * 0.5,
				self.z - half_l,
				self.z + half_l)

	def update(self, dt):
		# Move with world
		self.z += forward_speed * dt

	def is_past_player(self):
		return self.z > 2.0

	def draw(self):
		# Draw a slab slightly offset from the ground plane for visibility
		glPushMatrix()
		y_center = (-1.0 + self.thickness * 0.5) if self.side == "Floor" else (1.0 - self.thickness * 0.5)
		glTranslatef(LANE_X[self.lane_index], y_center, self.z)
		glColor3f(*self.color)
		glScalef(self.width, self.thickness, self.length)
		draw_cube(1.0)
		glPopMatrix()


class BreakablePlatform(Platform):
	def __init__(self, lane_index, side, z_center, break_delay=0.1):
		super().__init__(lane_index, side, z_center,
					 length=3.2, width=2.5, thickness=0.22,
					 color=(0.75, 0.35, 0.15))
		self.state = "intact"  # intact -> cracking -> broken
		self.time_since_step = 0.0
		self.break_delay = break_delay
		self.fragments = []  # list of dicts with pos (x,y,z), vel (vx,vy,vz), size

	def on_player_step(self):
		if self.state == "intact":
			self.state = "cracking"
			self.time_since_step = 0.0

	def _spawn_fragments(self):
		# Create a few falling cubes to simulate breaking
		rng = random.Random(hash((self.lane_index, int(self.z*10))) & 0xffffffff)
		for _ in range(8):
			fx = LANE_X[self.lane_index] + rng.uniform(-self.width*0.35, self.width*0.35)
			fz = self.z + rng.uniform(-self.length*0.35, self.length*0.35)
			fy = (-1.0 + self.thickness) if self.side == "Floor" else (1.0 - self.thickness)
			size = rng.uniform(0.12, 0.22)
			# initial velocity mostly away from the surface normal
			vy = rng.uniform(1.2, 2.0) * (1.0 if self.side == "Ceiling" else -1.0)
			vx = rng.uniform(-0.6, 0.6)
			vz = rng.uniform(-0.3, 0.3)
			self.fragments.append({
				"pos": [fx, fy, fz],
				"vel": [vx, vy, vz],
				"size": size,
			})

	def update(self, dt):
		super().update(dt)
		if self.state == "cracking":
			self.time_since_step += dt
			# change tint to indicate cracking
			phase = min(1.0, self.time_since_step / max(0.0001, self.break_delay))
			self.color = (0.26 + 0.5*phase, 0.22, 0.18)
			if self.time_since_step >= self.break_delay:
				self.state = "broken"
				self.collider_enabled = False
				self._spawn_fragments()
		elif self.state == "broken":
			# update fragments physics
			gravity = 6.0 * (1.0 if self.side == "Ceiling" else -1.0)
			for fr in self.fragments:
				fr["vel"][1] += gravity * dt
				fr["pos"][0] += fr["vel"][0] * dt
				fr["pos"][1] += fr["vel"][1] * dt
				fr["pos"][2] += fr["vel"][2] * dt

	def draw(self):
		# draw base slab (skip if fully broken but keep small remains tint)
		if self.state != "broken":
			glPushMatrix()
			y_center = (-1.0 + self.thickness * 0.5) if self.side == "Floor" else (1.0 - self.thickness * 0.5)
			glTranslatef(LANE_X[self.lane_index], y_center, self.z)
			# brighter crack tint while cracking
			if self.state == "cracking":
				phase = min(1.0, self.time_since_step / max(0.0001, self.break_delay))
				cr = self.color[0] * (1.0 - phase) + 1.0 * phase
				cg = self.color[1] * (1.0 - phase) + 0.20 * phase
				cb = self.color[2] * (1.0 - phase) + 0.10 * phase
				glColor3f(cr, cg, cb)
			else:
				glColor3f(*self.color)
			glScalef(self.width, self.thickness, self.length)
			draw_cube(1.0)
			glPopMatrix()

		# draw fragments
		if self.fragments:
			glColor3f(0.85, 0.55, 0.30)
			for fr in self.fragments:
				glPushMatrix()
				glTranslatef(fr["pos"][0], fr["pos"][1], fr["pos"][2])
				s = fr["size"]
				glScalef(s, s, s)
				draw_cube(1.0)
				glPopMatrix()


def reset_game():
	global obstacles, is_game_over, score, current_lane_index, last_time, current_surface, camera_roll_deg, target_roll_deg, platforms, difficulty_factor, forward_speed, current_difficulty_mode, spawn_cap_per_frame, collectibles, orbs_collected, car_fire_particles, cheat_active, cheat_until_ts, revive_available, waiting_for_revive_choice
	global invisibility_active, invisibility_until_ts, auto_flip_safety_active, auto_flip_until_ts, shield_active, shield_until_ts, inverted_controls_active, inverted_controls_until_ts, random_flip_active, random_flip_until_ts, random_flip_timer
	global wall_break_streak, combo_display_time, easy_path_active, easy_path_until_ts, tutorial_step, tutorial_timer
	
	is_game_over = False
	score = 0.0
	current_lane_index = 1
	obstacles = []
	platforms = []
	collectibles = []
	orbs_collected = 0
	car_fire_particles = []
	cheat_active = False
	cheat_until_ts = 0.0
	revive_available = False
	waiting_for_revive_choice = False
	last_time = time.time()
	current_surface = "Floor"
	camera_roll_deg = 0.0
	target_roll_deg = 0.0
	
	# Reset all abilities
	invisibility_active = False
	invisibility_until_ts = 0.0
	auto_flip_safety_active = False
	auto_flip_until_ts = 0.0
	shield_active = False
	shield_until_ts = 0.0
	inverted_controls_active = False
	inverted_controls_until_ts = 0.0
	random_flip_active = False
	random_flip_until_ts = 0.0
	random_flip_timer = 0.0
	
	# Reset combo system
	wall_break_streak = 0
	combo_display_time = 0.0
	
	# Reset easy path mode
	easy_path_active = False
	easy_path_until_ts = 0.0
	
	# Reset tutorial
	tutorial_step = 0
	tutorial_timer = 0.0
	
	# Reset difficulty and speed
	difficulty_factor = 1.0
	forward_speed = base_forward_speed
	current_difficulty_mode = "EASY"
	spawn_cap_per_frame = 1
	
	# Only initialize game elements if we have a theme and are playing
	if current_theme and game_state == "playing":
		seed_initial_obstacles()
		seed_initial_platforms()
		init_celestials_for_theme()
	
	glutPostRedisplay()


def seed_initial_obstacles():
	# Seed a few obstacles ahead
	acc = 12.0
	for _ in range(14):
		lane = random.randint(0, 2)
		size = 1.5
		side = "Floor" if random.random() < 0.5 else "Ceiling"
		# Choose type based on theme
		if current_theme:
			otype = choose_by_weights(get_theme_def()["obstacle_weights"])
		else:
			otype = "cube"
		obs = {"x": LANE_X[lane], "z": -acc, "size": size, "side": side, "type": otype}
		# Attach shape-specific params
		if otype == "ball":
			obs["radius"] = random.uniform(0.6, 1.1)
		elif otype == "drone":
			obs["radius"] = random.uniform(0.6, 0.9)
		elif otype == "cone":
			obs["radius"] = random.uniform(0.28, 0.38)
			obs["height"] = random.uniform(0.8, 1.1)
		elif otype == "pillar":
			obs["radius"] = random.uniform(0.26, 0.36)
			obs["height"] = random.uniform(1.2, 1.8)
		elif otype == "log":
			obs["radius"] = random.uniform(0.20, 0.30)
			obs["length"] = random.uniform(1.4, 2.2)
		elif otype == "ring":
			obs["inner"] = random.uniform(0.10, 0.16)
			obs["outer"] = random.uniform(0.8, 1.2)
		elif otype == "trap":
			obs["length"] = random.uniform(1.4, 2.2)
		obstacles.append(obs)
		acc += random.uniform(min_gap_z, min_gap_z + 4.0)




def seed_initial_platforms():
    	# Start with a few platforms staggered ahead on both sides
	acc = 10.0
	for _ in range(10):
		lane = random.randint(0, 2)
		side = "Floor" if random.random() < 0.5 else "Ceiling"
		# 60% chance to be breakable
		if random.random() < 0.6:
			platforms.append(BreakablePlatform(lane, side, -acc))
		else:
			platforms.append(Platform(lane, side, -acc))
		acc += random.uniform(platform_min_gap_z, platform_min_gap_z + 6.0)


def init():
	glClearColor(0.1, 0.12, 0.16, 1.0)
	glEnable(GL_DEPTH_TEST)
	glShadeModel(GL_SMOOTH)

	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	gluPerspective(60.0, width / float(height), 0.1, 200.0)

	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
	# Initialize celestial state for current theme
	init_celestials_for_theme()



def draw_text(x, y, text, font=None, color=(1.0, 1.0, 1.0)):
	if font is None:
		font = GLUT.GLUT_BITMAP_HELVETICA_18
	# Use current window viewport size for orthographic text placement
	vp = glGetIntegerv(GL_VIEWPORT)
	vp_w = vp[2] if isinstance(vp, (list, tuple)) else width
	vp_h = vp[3] if isinstance(vp, (list, tuple)) else height
	glMatrixMode(GL_PROJECTION)
	glPushMatrix()
	glLoadIdentity()
	gluOrtho2D(0, vp_w, 0, vp_h)
	glMatrixMode(GL_MODELVIEW)
	glPushMatrix()
	glLoadIdentity()
	glColor3f(*color)
	glRasterPos2f(x, y)
	for ch in text:
		glutBitmapCharacter(font, ord(ch))
	glPopMatrix()
	glMatrixMode(GL_PROJECTION)
	glPopMatrix()
	glMatrixMode(GL_MODELVIEW)


# Backward compatibility: route any legacy calls to draw_text
def draw_text_2d(x, y, text, font=None, color=(1.0, 1.0, 1.0)):
	return draw_text(x, y, text, font=font, color=color)


def draw_ground_and_lanes():
	# Draw only the current surface to avoid occluding the scene
	glBegin(GL_QUADS)
	ground_col = get_theme_def()["ground_color"]
	if current_surface == "Floor":
		glColor3f(*ground_col)
		glVertex3f(-8.0, -1.0, 5.0)
		glVertex3f(8.0, -1.0, 5.0)
		glVertex3f(8.0, -1.0, -200.0)
		glVertex3f(-8.0, -1.0, -200.0)
	else:
		glColor3f(ground_col[0]*0.9, ground_col[1]*0.9, ground_col[2]*0.9)
		glVertex3f(-8.0, 1.0, 5.0)
		glVertex3f(8.0, 1.0, 5.0)
		glVertex3f(8.0, 1.0, -200.0)
		glVertex3f(-8.0, 1.0, -200.0)
	glEnd()

	# Lane lines on the current surface
	glLineWidth(2.0)
	lc = get_theme_def()["lane_color"]
	glColor3f(*lc)
	glBegin(GL_LINES)
	for x in [-1.25, 1.25]:
		z = 5.0
		y = -0.999 if current_surface == "Floor" else 0.999
		while z > -200.0:
			glVertex3f(x, y, z)
			glVertex3f(x, y, z - 2.0)
			z -= 4.0
	glEnd()


def draw_cube(size):
	# Simple cube centered at origin
	s = size * 0.5
	glBegin(GL_QUADS)
	# +X
	glNormal3f(1, 0, 0)
	glVertex3f(s, -s, -s)
	glVertex3f(s, -s, s)
	glVertex3f(s, s, s)
	glVertex3f(s, s, -s)
	# -X
	glNormal3f(-1, 0, 0)
	glVertex3f(-s, -s, s)
	glVertex3f(-s, -s, -s)
	glVertex3f(-s, s, -s)
	glVertex3f(-s, s, s)
	# +Y
	glNormal3f(0, 1, 0)
	glVertex3f(-s, s, -s)
	glVertex3f(s, s, -s)
	glVertex3f(s, s, s)
	glVertex3f(-s, s, s)
	# -Y
	glNormal3f(0, -1, 0)
	glVertex3f(-s, -s, s)
	glVertex3f(s, -s, s)
	glVertex3f(s, -s, -s)
	glVertex3f(-s, -s, -s)
	# +Z
	glNormal3f(0, 0, 1)
	glVertex3f(-s, -s, s)
	glVertex3f(-s, s, s)
	glVertex3f(s, s, s)
	glVertex3f(s, -s, s)
	# -Z
	glNormal3f(0, 0, -1)
	glVertex3f(s, -s, -s)
	glVertex3f(s, s, -s)
	glVertex3f(-s, s, -s)
	glVertex3f(-s, -s, -s)
	glEnd()


# -------------------- Celestial Drawing --------------------
def _sky_push_camera():
	"""Place drawing far away so it sits behind gameplay. Keep current camera/roll."""
	# We rely on current camera + roll already set in display(); just ensure depth writes minimal.
	glDisable(GL_LIGHTING)
	glDepthMask(GL_TRUE)

def draw_stars():
	if celestial_fade <= 0.01 or not stars:
		return
	_sky_push_camera()
	# Soft additive-like draw: enable blending
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE)
	for s in stars:
		x, y, z = s["pos"]
		sz = s["size"]
		phase = s["phase"]
		alpha = 0.3 + 0.7 * abs(math.sin(phase))
		alpha *= celestial_fade
		glColor4f(celestial_palette["stars"][0], celestial_palette["stars"][1], celestial_palette["stars"][2], alpha)
		glPushMatrix()
		glTranslatef(x, y, z)
		# Render tiny billboard quad (screen-facing approximation)
		s = sz
		glBegin(GL_QUADS)
		glVertex3f(-s, -s, 0)
		glVertex3f(s, -s, 0)
		glVertex3f(s, s, 0)
		glVertex3f(-s, s, 0)
		glEnd()
		glPopMatrix()
	glDisable(GL_BLEND)


def draw_sun():
	if celestial_fade <= 0.01:
		return
	_sky_push_camera()
	# Fixed position in sky hemisphere for day themes
	glPushMatrix()
	# Place within frustum top band
	x = (SKY_X_RANGE[0]*0.35)
	y = SKY_Y_RANGE[1] - 1.0
	z = (SKY_Z_RANGE[0]+SKY_Z_RANGE[1]) * 0.5
	glTranslatef(x, y, z)
	glColor4f(celestial_palette["sun"][0], celestial_palette["sun"][1], celestial_palette["sun"][2], 1.0 * celestial_fade)
	glutSolidSphere(0.9, 22, 18)
	# Glow halo quad
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE)
	glColor4f(celestial_palette["sun"][0], celestial_palette["sun"][1], celestial_palette["sun"][2], 0.27 * celestial_fade)
	glBegin(GL_QUADS)
	glVertex3f(-1.8, -1.8, 0.0)
	glVertex3f(1.8, -1.8, 0.0)
	glVertex3f(1.8, 1.8, 0.0)
	glVertex3f(-1.8, 1.8, 0.0)
	glEnd()
	glDisable(GL_BLEND)
	glPopMatrix()


def draw_moon():
	if celestial_fade <= 0.01:
		return
	_sky_push_camera()
	glPushMatrix()
	# Place within frustum top band opposite the sun
	x = (SKY_X_RANGE[1]*0.35)
	y = SKY_Y_RANGE[1] - 1.2
	z = (SKY_Z_RANGE[0]+SKY_Z_RANGE[1]) * 0.45
	glTranslatef(x, y, z)
	glColor4f(celestial_palette["moon"][0], celestial_palette["moon"][1], celestial_palette["moon"][2], 1.0 * celestial_fade)
	glutSolidSphere(0.8, 20, 16)
	# Subtle craterish shading via overlay quads
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	glColor4f(0.85, 0.85, 0.85, 0.25 * celestial_fade)
	for ox, oy, r in ((-0.2, 0.15, 0.35), (0.25, -0.1, 0.28), (0.1, 0.25, 0.22)):
		glPushMatrix()
		glTranslatef(ox, oy, 0.4)
		glScalef(r, r, r)
		glBegin(GL_QUADS)
		glVertex3f(-1, -1, 0)
		glVertex3f(1, -1, 0)
		glVertex3f(1, 1, 0)
		glVertex3f(-1, 1, 0)
		glEnd()
		glPopMatrix()
	glDisable(GL_BLEND)
	glPopMatrix()


def draw_clouds():
	if celestial_fade <= 0.01 or not clouds:
		return
	_sky_push_camera()
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	for c in clouds:
		x, y, z = c["pos"]
		sz = c["size"]
		alpha = min(0.8, 0.45 + 0.35 * (1.0 - abs(math.sin(c.get("phase", 0.0))))) * celestial_fade
		glColor4f(0.95, 0.97, 1.0, alpha)
		glPushMatrix()
		glTranslatef(x, y, z)
		glScalef(sz*2.0, sz*0.8, 1.0)
		glBegin(GL_QUADS)
		glVertex3f(-1, -0.6, 0)
		glVertex3f(1, -0.6, 0)
		glVertex3f(1, 0.6, 0)
		glVertex3f(-1, 0.6, 0)
		glEnd()
		glPopMatrix()
	glDisable(GL_BLEND)


def draw_rain():
	if celestial_fade <= 0.01 or not raindrops:
		return
	_sky_push_camera()
	# Rain should appear after clouds but before comets/UFOs; blending on
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	# Draw falling drops
	glColor4f(0.8, 0.9, 1.0, 0.7 * celestial_fade)
	glBegin(GL_LINES)
	for r in raindrops:
		if not r.get("alive", True):
			continue
		x, y, z = r["pos"]
		vx, vy, vz = r["vel"]
		length = r.get("len", RAIN_LENGTH)
		lx = vx / max(1e-6, math.sqrt(vx*vx + vy*vy + vz*vz)) * length
		ly = vy / max(1e-6, math.sqrt(vx*vx + vy*vy + vz*vz)) * length
		lz = vz / max(1e-6, math.sqrt(vx*vx + vy*vy + vz*vz)) * length
		glVertex3f(x, y, z)
		glVertex3f(x - lx, y - ly, z - lz)
	glEnd()
	# Draw splashes
	glColor4f(0.85, 0.95, 1.0, 0.45 * celestial_fade)
	glBegin(GL_LINES)
	for r in raindrops:
		if r.get("alive", True) or r.get("splash", 0.0) <= 0.0:
			continue
		x, y, z = r["pos"]
		s = 0.12 * r["splash"]
		glVertex3f(x - s, GROUND_Y + 0.02, z)
		glVertex3f(x + s, GROUND_Y + 0.02, z)
	glEnd()
	glDisable(GL_BLEND)


def draw_ufos():
	if celestial_fade <= 0.01 or not ufos:
		return
	_sky_push_camera()
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE)
	for u in ufos:
		x, y, z = u["pos"]
		phase = u.get("phase", 0.0)
		wobble = 0.12 * math.sin(phase * 2.5)
		# Glow disc
		glPushMatrix()
		glTranslatef(x, y + wobble, z)
		glColor4f(0.6, 0.9, 1.0, 0.9 * celestial_fade)
		glBegin(GL_TRIANGLE_FAN)
		glVertex3f(0, 0, 0)
		for i in range(0, 26):
			ang = (i/25.0) * 6.28318
			r = 0.5
			glVertex3f(math.cos(ang)*r, math.sin(ang)*r*0.45, 0)
		glEnd()
		# Dome
		glColor4f(0.8, 0.95, 1.0, 0.65 * celestial_fade)
		glPushMatrix()
		glTranslatef(0, 0.12, 0)
		glutSolidSphere(0.22, 12, 10)
		glPopMatrix()
		glPopMatrix()
	glDisable(GL_BLEND)


def draw_comet():
	if celestial_fade <= 0.01 or not comets:
		return
	_sky_push_camera()
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE)
	for c in comets:
		# head
		hx, hy, hz = c["pos"]
		glColor4f(1.0, 0.95, 0.85, 0.95 * celestial_fade)
		glPushMatrix()
		glTranslatef(hx, hy, hz)
		glutSolidSphere(comet_head_radius, 12, 10)
		glPopMatrix()
		# tail segments
		for seg in c.get("tail", [])[-comet_tail_max:]:
			px, py, pz = seg["pos"]
			age = seg["life"]
			alpha = max(0.0, min(1.0, age)) * 0.55 * celestial_fade
			clr = celestial_palette["comet_tail"]
			glColor4f(clr[0], clr[1], clr[2], alpha)
			glPushMatrix()
			glTranslatef(px, py, pz)
			s = 0.10 * (0.6 + 0.4 * age)
			glBegin(GL_QUADS)
			glVertex3f(-s, -s, 0)
			glVertex3f(s, -s, 0)
			glVertex3f(s, s, 0)
			glVertex3f(-s, s, 0)
			glEnd()
			glPopMatrix()
	glDisable(GL_BLEND)


def draw_box(scale_x, scale_y, scale_z, color=None):
	"""Draw a box by scaling a unit cube."""
	glPushMatrix()
	if color is not None:
		glColor3f(*color)
	glScalef(scale_x, scale_y, scale_z)
	draw_cube(1.0)
	glPopMatrix()


def draw_car():
	"""Draw a simple car model centered at origin facing -Z."""
	# Dimensions
	body_len = 1.2
	body_wid = 0.8
	body_hei = 0.28
	cabin_len = 0.6
	cabin_wid = 0.72
	cabin_hei = 0.28
	wheel_outer = 0.12
	wheel_inner = 0.05

	# Color palette: normal vs cheat mode (greyed)
	if cheat_active:
		color_body = (0.55, 0.55, 0.58)
		color_cabin = (0.62, 0.62, 0.66)
		color_hood = (0.60, 0.60, 0.64)
		color_wheel = (0.35, 0.35, 0.35)
	else:
		color_body = (0.15, 0.5, 0.95)
		color_cabin = (0.14, 0.42, 0.82)
		color_hood = (0.17, 0.55, 0.98)
		color_wheel = (0.08, 0.08, 0.08)

	# Lower body (chassis)
	glPushMatrix()
	glTranslatef(0.0, -0.1, 0.0)
	draw_box(body_wid, body_hei, body_len, color=color_body)
	glPopMatrix()

	# Cabin (top)
	glPushMatrix()
	# Shift slightly towards the back (positive Z is toward camera, front is -Z)
	glTranslatef(0.0, 0.1, 0.1)
	draw_box(cabin_wid, cabin_hei, cabin_len, color=color_cabin)
	glPopMatrix()

	# Hood (front block)
	glPushMatrix()
	glTranslatef(0.0, -0.02, -0.35)
	draw_box(cabin_wid * 0.9, body_hei * 0.6, 0.35, color=color_hood)
	glPopMatrix()

	# Wheels (tori)
	glColor3f(*color_wheel)
	z_offset = body_len * 0.35
	x_offset = body_wid * 0.5
	y_wheel = -0.1 - (body_hei * 0.5) - 0.02
	for x in (-x_offset, x_offset):
		for z in (-z_offset, z_offset):
			glPushMatrix()
			glTranslatef(x, y_wheel, z)
			# Orient the torus so its axis is roughly along X for a wheel-like look
			glRotatef(90, 0, 1, 0)
			glutSolidTorus(wheel_inner, wheel_outer, 16, 24)
			glPopMatrix()


def draw_player():
	glPushMatrix()
	y_player = -0.25 if current_surface == "Floor" else 0.25
	glTranslatef(LANE_X[current_lane_index], y_player, player_z_offset)
	# Keep the car visually upright: counter-rotate against camera roll
	glRotatef(-camera_roll_deg, 0.0, 0.0, 1.0)
	# Slightly scale up the car so it stands out
	glScalef(1.3, 1.3, 1.3)
	if cheat_active:
		# render car in grey tone overlay by tinting parts via a global material color
		glColor3f(0.6, 0.6, 0.6)
		draw_box(0.0, 0.0, 0.0)  # no-op to set color; parts below set their own colors
	# draw car with its internal colors; cheat tint will be visible on uncolored primitives only
	draw_car()
	glPopMatrix()


def trigger_car_fire_effect():
	"""Spawn a brief burning effect around player car when trap coin hits."""
	global car_fire_particles
	car_fire_particles = []
	rng = random.Random(hash((int(time.time()*1000), 12345)) & 0xffffffff)
	y_car = (-0.25) if current_surface == "Floor" else 0.25
	base_x = LANE_X[current_lane_index]
	base_z = player_z_offset
	for _ in range(36):
		xj = rng.uniform(-0.35, 0.35)
		zj = rng.uniform(-0.35, 0.35)
		vy = rng.uniform(1.8, 3.2) * (1.0 if current_surface == "Ceiling" else -1.0)
		vx = rng.uniform(-0.5, 0.5)
		vz = rng.uniform(-0.5, 0.5)
		car_fire_particles.append({
			"pos": [base_x + xj, y_car, base_z + zj],
			"vel": [vx, vy, vz],
			"life": car_fire_max_life,
			"color": (1.0, rng.uniform(0.35, 0.7), 0.15),
			"size": rng.uniform(0.12, 0.22),
		})


def update_car_fire_effect(dt):
	if not car_fire_particles:
		return
	gravity = 7.5 * (1.0 if current_surface == "Ceiling" else -1.0)
	for p in car_fire_particles:
		p["vel"][1] += gravity * dt
		p["pos"][0] += p["vel"][0] * dt
		p["pos"][1] += p["vel"][1] * dt
		p["pos"][2] += p["vel"][2] * dt
		p["life"] -= dt
	# prune
	alive = [p for p in car_fire_particles if p["life"] > 0]
	car_fire_particles[:] = alive


def draw_obstacles():
	for obs in obstacles:
		# Draw only current-surface obstacles to avoid occlusion/confusion during flips
		if obs.get("side", "Floor") != current_surface:
			continue
		otype = obs.get("type", "cube")
		glPushMatrix()
		y_base = -0.25 if obs.get("side", "Floor") == "Floor" else 0.25
		glTranslatef(obs["x"], y_base, obs["z"])

		if otype == "trap":
			# Flat, wide hazard tile
			glColor3f(0.95, 0.55, 0.15)
			# trap dimensions scaled from size
			tw = 1.8
			th = 0.12
			tl = max(1.2, obs.get("length", 1.6))
			glPushMatrix()
			glScalef(tw, th, tl)
			draw_cube(1.0)
			glPopMatrix()
		elif otype == "car":
			# City car/barrier combo: draw a low-profile rectangular car
			glColor3f(0.2, 0.2, 0.22)
			glPushMatrix()
			glTranslatef(0.0, 0.0, 0.0)
			glScalef(0.9, 0.4, 1.4)
			draw_cube(1.0)
			glPopMatrix()
		elif otype == "bus":
			# City bus: long rectangular prism, bright color
			glColor3f(0.95, 0.85, 0.15)
			glPushMatrix()
			glScalef(0.9, 0.6, 2.0)
			draw_cube(1.0)
			glPopMatrix()
		elif otype == "barrier":
			# City barrier
			glColor3f(0.7, 0.1, 0.1)
			glPushMatrix()
			glScalef(1.0, 0.7, 0.5)
			draw_cube(1.0)
			glPopMatrix()
		elif otype == "cone":
			# City traffic cone
			glColor3f(1.0, 0.45, 0.1)
			glPushMatrix()
			# base offset a bit so it rests on surface nicely
			glTranslatef(0.0, 0.05 * (1.0 if obs.get("side", "Floor") == "Floor" else -1.0), 0.0)
			r = max(0.3, obs.get("radius", 0.35))
			h = max(0.6, obs.get("height", 0.9))
			glRotatef(-90 if current_surface == "Floor" else 90, 1, 0, 0)
			glutSolidCone(r, h, 16, 8)
			glPopMatrix()
		elif otype == "stone":
			# Jungle stone block
			glColor3f(0.35, 0.35, 0.32)
			glPushMatrix()
			glScalef(1.2, 0.9, 1.0)
			draw_cube(1.0)
			glPopMatrix()
		elif otype == "pillar":
			# Jungle stone pillar (cylinder)
			glColor3f(0.32, 0.34, 0.30)
			glPushMatrix()
			r = max(0.25, obs.get("radius", 0.3))
			h = max(1.2, obs.get("height", 1.6))
			q = gluNewQuadric()
			# orient up from surface
			glTranslatef(0.0, (h*0.5 - 0.1) * (1.0 if obs.get("side", "Floor") == "Floor" else -1.0), 0.0)
			glRotatef(-90 if current_surface == "Floor" else 90, 1, 0, 0)
			gluCylinder(q, r, r, h, 16, 1)
			glPopMatrix()
		elif otype == "log":
			# Jungle fallen log (horizontal cylinder)
			glColor3f(0.45, 0.30, 0.16)
			glPushMatrix()
			r = max(0.20, obs.get("radius", 0.25))
			lz = max(1.2, obs.get("length", 1.8))
			q = gluNewQuadric()
			# orient across lane (X axis)
			glRotatef(90, 0, 1, 0)
			glRotatef(-90 if current_surface == "Floor" else 90, 1, 0, 0)
			gluCylinder(q, r, r, lz, 16, 1)
			glPopMatrix()
		elif otype == "drone":
			# Space floating drone
			glColor3f(0.6, 0.8, 1.0)
			radius = max(0.45, obs.get("radius", 0.7))
			lift = radius * 0.6 * (1.0 if obs.get("side", "Floor") == "Floor" else -1.0)
			glTranslatef(0.0, lift, 0.0)
			glutSolidSphere(radius, 20, 16)
		elif otype == "ring":
			# Space ring (torus) to dodge through
			glColor3f(0.45, 0.75, 1.0)
			inner = max(0.08, obs.get("inner", 0.12))
			outer = max(0.6, obs.get("outer", 0.9))
			glRotatef(90, 1, 0, 0)
			glutSolidTorus(inner, outer, 16, 28)
		elif otype == "gate":
			# Space gate: two pillars + top beam
			glColor3f(0.7, 0.85, 1.0)
			glPushMatrix()
			# left pillar
			glPushMatrix()
			glTranslatef(-0.7, 0.0, 0.0)
			glScalef(0.2, 1.2, 0.2)
			draw_cube(1.0)
			glPopMatrix()
			# right pillar
			glPushMatrix()
			glTranslatef(0.7, 0.0, 0.0)
			glScalef(0.2, 1.2, 0.2)
			draw_cube(1.0)
			glPopMatrix()
			# top beam
			glPushMatrix()
			glTranslatef(0.0, 0.7 if current_surface == "Floor" else -0.7, 0.0)
			glScalef(1.6, 0.2, 0.2)
			draw_cube(1.0)
			glPopMatrix()
			glPopMatrix()
		elif otype == "wall":
			# Breakable wall panel across the lane
			glColor3f(0.75, 0.75, 0.80)
			width = obs.get("width", 1.8)
			height = obs.get("height", 0.9)
			thickness = obs.get("thickness", 0.10)  # slim visual thickness
			glPushMatrix()
			# lift wall so its center is above the ground/ceiling a bit
			lift = (height * 0.5 + 0.1) * (1.0 if obs.get("side", "Floor") == "Floor" else -1.0)
			glTranslatef(0.0, lift, 0.0)
			glScalef(width, height, thickness)
			draw_cube(1.0)
			glPopMatrix()
		elif otype == "moving_spike":
			# Moving spikes that slide across lanes
			glColor3f(0.9, 0.1, 0.1)
			spike_count = obs.get("spike_count", 4)
			for i in range(spike_count):
				glPushMatrix()
				offset = (i - spike_count/2) * 0.3
				glTranslatef(offset, 0.0, 0.0)
				glRotatef(-90 if current_surface == "Floor" else 90, 1, 0, 0)
				glutSolidCone(0.15, 0.6, 8, 1)
				glPopMatrix()
		elif otype == "rotating_blade":
			# Rotating blade obstacles
			glColor3f(0.8, 0.8, 0.9)
			rotation = obs.get("rotation", 0.0)
			blade_radius = obs.get("blade_radius", 1.0)
			blade_count = obs.get("blade_count", 4)
			glPushMatrix()
			glRotatef(rotation, 0, 1, 0)
			for i in range(blade_count):
				angle = (360.0 / blade_count) * i
				glPushMatrix()
				glRotatef(angle, 0, 1, 0)
				glTranslatef(blade_radius * 0.5, 0, 0)
				glScalef(blade_radius, 0.1, 0.2)
				draw_cube(1.0)
				glPopMatrix()
			glPopMatrix()
		elif otype == "electric_wall":
			# Electric wall with pulsing energy
			energy = obs.get("energy", 1.0)
			glColor3f(0.2 + 0.6 * energy, 0.8 * energy, 1.0)
			width = obs.get("width", 1.8)
			height = obs.get("height", 0.9)
			thickness = obs.get("thickness", 0.10)
			glPushMatrix()
			lift = (height * 0.5 + 0.1) * (1.0 if obs.get("side", "Floor") == "Floor" else -1.0)
			glTranslatef(0.0, lift, 0.0)
			glScalef(width, height, thickness)
			draw_cube(1.0)
			# Add electric sparks effect
			glColor3f(1.0, 1.0 * energy, 0.8)
			for _ in range(int(5 * energy)):
				spark_x = random.uniform(-width*0.4, width*0.4)
				spark_y = random.uniform(-height*0.4, height*0.4)
				glPushMatrix()
				glTranslatef(spark_x, spark_y, thickness*0.6)
				glScalef(0.1, 0.1, 0.1)
				draw_cube(1.0)
				glPopMatrix()
			glPopMatrix()
		elif otype == "ball":
			# Spherical obstacle (same color as cube)
			glColor3f(0.9, 0.3, 0.3)
			radius = max(0.5, obs.get("radius", obs.get("size", 1.0) * 0.6))
			lift = radius * 0.6 * (1.0 if obs.get("side", "Floor") == "Floor" else -1.0)
			glTranslatef(0.0, lift, 0.0)
			glutSolidSphere(radius, 22, 18)
		else:
			# Default cube obstacle
			glColor3f(0.9, 0.3, 0.3)
			draw_cube(obs.get("size", 1.5))

		glPopMatrix()


class Collectible:
	def __init__(self, lane_index, side, z_center, radius=0.25, base_color=(0.2, 0.9, 1.0)):
		self.lane_index = lane_index
		self.side = side  # "Floor" or "Ceiling"
		self.z = z_center
		self.radius = radius
		self.base_color = base_color
		self.alive = True
		self.rot_deg = 0.0
		self.collected_at = None

	def collect(self):
		self.alive = False
		self.collected_at = time.time()

	def update(self, dt):
		self.z += forward_speed * dt
		self.rot_deg = (self.rot_deg + 120.0 * dt) % 360.0

	def is_past_player(self):
		if (not self.alive) and (self.collected_at is None):
			return True
		if self.z > 2.0:
			return True
		if self.collected_at is not None and (time.time() - self.collected_at) > 0.25:
			return True
		return False

	def draw(self):
		if self.collected_at is not None:
			age = time.time() - self.collected_at
			if age > 0.25:
				return
			glPushMatrix()
			y = (-0.6) if self.side == "Floor" else 0.6
			glTranslatef(LANE_X[self.lane_index], y, self.z)
			scale = 1.0 + 2.0 * age
			glScalef(scale, scale, scale)
			glColor3f(self.base_color[0], self.base_color[1], self.base_color[2])
			glutSolidSphere(self.radius * 0.6, 12, 10)
			glPopMatrix()
			return
		if not self.alive:
			return
		glPushMatrix()
		y = (-0.6) if self.side == "Floor" else 0.6
		glTranslatef(LANE_X[self.lane_index], y, self.z)
		glRotatef(self.rot_deg, 0.0, 1.0, 0.0)
		pulse = 0.6 + 0.4 * abs((time.time() * 2.0) % 2.0 - 1.0)
		glColor3f(self.base_color[0] * pulse, self.base_color[1] * pulse, self.base_color[2] * pulse)
		glutSolidSphere(self.radius, 16, 12)
		glPopMatrix()


class Coin(Collectible):
	def __init__(self, lane_index, side, z_center, coin_type="normal"):
		self.coin_type = coin_type  # "normal" or "trap"
		base = (0.95, 0.8, 0.15) if coin_type == "normal" else (1.0, 0.35, 0.15)
		super().__init__(lane_index, side, z_center, radius=0.22, base_color=base)
		self.explosion_particles = []
		self.explosion_max_life = 0.6

	def collect(self):
		if self.coin_type == "trap":
			self._spawn_explosion()
			self.collected_at = time.time()
			self.alive = False
		else:
			self.alive = False
			self.collected_at = None

	def _spawn_explosion(self):
		rng = random.Random(hash((self.lane_index, int(self.z*1000), 17)) & 0xffffffff)
		y = (-0.6) if self.side == "Floor" else 0.6
		for _ in range(18):
			ang = rng.uniform(0, 6.28318)
			speed = rng.uniform(1.5, 3.0)
			vx = speed * math.cos(ang)
			vz = speed * math.sin(ang)
			vy = rng.uniform(1.0, 2.2) * (1.0 if self.side == "Ceiling" else -1.0)
			self.explosion_particles.append({
				"pos": [LANE_X[self.lane_index], y, self.z],
				"vel": [vx, vy, vz],
				"life": self.explosion_max_life,
				"color": (1.0, rng.uniform(0.3, 0.6), 0.1),
				"size": rng.uniform(0.06, 0.12),
			})

	def update(self, dt):
		super().update(dt)
		if self.explosion_particles:
			gravity = 7.0 * (1.0 if self.side == "Ceiling" else -1.0)
			for p in self.explosion_particles:
				p["vel"][1] += gravity * dt
				p["pos"][0] += p["vel"][0] * dt
				p["pos"][1] += p["vel"][1] * dt
				p["pos"][2] += p["vel"][2] * dt
				p["life"] -= dt
			self.explosion_particles = [p for p in self.explosion_particles if p["life"] > 0]

	def is_past_player(self):
		if self.explosion_particles:
			return False
		return super().is_past_player()

	def draw(self):
		if self.explosion_particles:
			for p in self.explosion_particles:
				glPushMatrix()
				glTranslatef(p["pos"][0], p["pos"][1], p["pos"][2])
				glColor3f(*p["color"])
				s = p["size"] * (0.6 + 0.4 * (p["life"] / self.explosion_max_life))
				glScalef(s, s, s)
				draw_cube(1.0)
				glPopMatrix()
			if self.collected_at is not None:
				age = time.time() - self.collected_at
				if age < self.explosion_max_life:
					glPushMatrix()
					y = (-0.6) if self.side == "Floor" else 0.6
					glTranslatef(LANE_X[self.lane_index], y, self.z)
					fade = max(0.0, 1.0 - (age / self.explosion_max_life))
					glColor3f(self.base_color[0], self.base_color[1] * 0.6, self.base_color[2] * 0.4)
					glutSolidSphere(self.radius * 0.18 * (1.0 + 2.0 * (1.0 - fade)), 10, 8)
					glPopMatrix()
			return
		return super().draw()



def _effective_obstacle_params():
	"""Compute spawn parameters based on current difficulty."""
	# As difficulty rises, reduce spacing and increase spawn frequency window
	f = max(1.0, difficulty_factor)
	gap_scale = max(0.35, 1.0 - 0.10 * (f - 1.0))
	# Mode-based tightening
	if current_difficulty_mode == "MEDIUM":
		gap_scale *= 0.85
	elif current_difficulty_mode == "HARD":
		gap_scale *= 0.70
	eff_min_gap = max(1.0, min_gap_z * gap_scale)
	eff_spawn_min = max(6.0, spawn_distance_min * gap_scale)
	eff_spawn_max = max(eff_spawn_min + 2.0, spawn_distance_max * gap_scale)
	return eff_min_gap, eff_spawn_min, eff_spawn_max


def try_spawn_obstacles():
	# Ensure there is always something far ahead
	if not obstacles:
		seed_initial_obstacles()
		return

	# Potentially spawn multiple obstacles to increase density with difficulty
	eff_min_gap, eff_spawn_min, eff_spawn_max = _effective_obstacle_params()
	spawned = 0
	while True:
		max_forward = min(o["z"] for o in obstacles)
		if max_forward <= -eff_spawn_min:
			break
		lane = random.randint(0, 2)
		size = 1.5
		target_z = max_forward - random.uniform(eff_spawn_min, eff_spawn_max)
		# keep lane spacing: avoid placing if there is an obstacle too close in same lane
		same_lane = [o for o in obstacles if o["x"] == LANE_X[lane]]
		if same_lane:
			closest_ahead = min(o["z"] for o in same_lane)
			if target_z - closest_ahead > -(eff_min_gap):
				target_z = closest_ahead - eff_min_gap
		side = "Floor" if random.random() < 0.5 else "Ceiling"
		# Enhanced obstacle type selection based on difficulty and theme
		if easy_path_active:
			# No obstacles during easy path mode, only coins
			continue
			
		enhanced_types = ["moving_spike", "rotating_blade", "electric_wall"]
		
		if current_difficulty_mode == "HARD" and random.random() < 0.3:
			# 30% chance for enhanced obstacles in hard mode
			otype = random.choice(enhanced_types)
			obs = create_enhanced_obstacle(lane, target_z, side, otype)
		elif random.random() < 0.40:
			otype = "wall"
			obs = {"x": LANE_X[lane], "z": target_z, "size": size, "side": side, "type": otype}
		else:
			if current_theme:
				otype = choose_by_weights(get_theme_def()["obstacle_weights"])  # theme-provided (no walls here)
			else:
				if current_difficulty_mode == "EASY":
					otype = "cube"
				elif current_difficulty_mode == "MEDIUM":
					otype = "trap" if random.random() < 0.6 else "cube"
				else:  # HARD
					roll_other = random.random()
					if roll_other < 0.45:
						otype = "ball"
					elif roll_other < 0.80:
						otype = "trap"
					else:
						otype = "cube"
			obs = {"x": LANE_X[lane], "z": target_z, "size": size, "side": side, "type": otype}
		if otype == "ball":
			obs["radius"] = random.uniform(0.6, 1.1)
		elif otype == "drone":
			obs["radius"] = random.uniform(0.6, 0.9)
		elif otype == "cone":
			obs["radius"] = random.uniform(0.28, 0.38)
			obs["height"] = random.uniform(0.8, 1.1)
		elif otype == "pillar":
			obs["radius"] = random.uniform(0.26, 0.36)
			obs["height"] = random.uniform(1.2, 1.8)
		elif otype == "log":
			obs["radius"] = random.uniform(0.20, 0.30)
			obs["length"] = random.uniform(1.4, 2.2)
		elif otype == "ring":
			obs["inner"] = random.uniform(0.10, 0.16)
			obs["outer"] = random.uniform(0.8, 1.2)
		elif otype == "trap":
			obs["length"] = random.uniform(1.4, 2.2)
		elif otype == "wall":
			obs["width"] = random.uniform(1.6, 2.0)
			obs["height"] = random.uniform(0.8, 1.2)
			obs["thickness"] = random.uniform(0.18, 0.28)
		obstacles.append(obs)
		spawned += 1
		# Cap spawns per frame depending on mode
		if spawned >= spawn_cap_per_frame:
			break

	# Removed forced per-lane wall injection to target ~40% walls overall

	# Guarantee a minimum number of obstacles present by topping up beyond per-frame cap
	fill_safety = 0
	while len(obstacles) < min_obstacles_on_screen and fill_safety < 24:
		fill_safety += 1
		max_forward = min(o["z"] for o in obstacles)
		lane = random.randint(0, 2)
		size = 1.5
		target_z = max_forward - random.uniform(eff_spawn_min, eff_spawn_max)
		same_lane = [o for o in obstacles if o["x"] == LANE_X[lane]]
		if same_lane:
			closest_ahead = min(o["z"] for o in same_lane)
			if target_z - closest_ahead > -(eff_min_gap):
				target_z = closest_ahead - eff_min_gap
		side = "Floor" if random.random() < 0.5 else "Ceiling"
		# 40% walls, 60% others for top-up as well
		if random.random() < 0.40:
			otype = "wall"
		else:
			if current_theme:
				otype = choose_by_weights(get_theme_def()["obstacle_weights"])  # theme-provided (no walls here)
			else:
				if current_difficulty_mode == "EASY":
					otype = "cube"
				elif current_difficulty_mode == "MEDIUM":
					otype = "trap" if random.random() < 0.6 else "cube"
				else:
					roll_other = random.random()
					if roll_other < 0.45:
						otype = "ball"
					elif roll_other < 0.80:
						otype = "trap"
					else:
						otype = "cube"
		dobs = {"x": LANE_X[lane], "z": target_z, "size": size, "side": side, "type": otype}
		if otype == "ball":
			dobs["radius"] = random.uniform(0.6, 1.1)
		elif otype == "trap":
			dobs["length"] = random.uniform(1.4, 2.2)
		elif otype == "wall":
			dobs["width"] = random.uniform(1.6, 2.0)
			dobs["height"] = random.uniform(0.8, 1.2)
			dobs["thickness"] = random.uniform(0.18, 0.28)
		obstacles.append(dobs)


def try_spawn_platforms():
	# Ensure a platform field stretches forward sufficiently
	if not platforms:
		seed_initial_platforms()
		return

	max_forward = min(p.z for p in platforms)
	if max_forward > -platform_spawn_min:
		lane = random.randint(0, 2)
		side = "Floor" if random.random() < 0.5 else "Ceiling"
		target_z = max_forward - random.uniform(platform_spawn_min, platform_spawn_max)
		# spacing in same lane+side
		same_lane_side = [p for p in platforms if p.lane_index == lane and p.side == side]
		if same_lane_side:
			closest_ahead = min(p.z for p in same_lane_side)
			if target_z - closest_ahead > -(platform_min_gap_z * 0.8):
				target_z = closest_ahead - (platform_min_gap_z * 0.8)
		# choose type
		if random.random() < 0.55:
			platforms.append(BreakablePlatform(lane, side, target_z))
		else:
			platforms.append(Platform(lane, side, target_z))


def try_spawn_collectibles():
	# Spawn coins slightly above platforms and reachable
	if not platforms:
		return
	max_forward = min(p.z for p in platforms)
	alive_coins = [c for c in collectibles if isinstance(c, Collectible) and c.alive and c.collected_at is None]
	need_spawn = not alive_coins
	if alive_coins:
		furthest = min(c.z for c in alive_coins)
		need_spawn = furthest > (max_forward + orb_spawn_min_gap)
	if need_spawn:
		candidates = [p for p in platforms if p.z <= max_forward + 5.0] or platforms
		host = random.choice(candidates)
		target_z = max_forward - random.uniform(orb_spawn_min_gap, orb_spawn_max_gap)
		lane = host.lane_index
		side = host.side
		coin_type = "trap" if random.random() < 0.15 else "normal"
		collectibles.append(Coin(lane, side, target_z, coin_type=coin_type))

	# Ensure at least one alive orb present in each lane every frame
	# Prefer current surface for visibility. Use nearby platforms if possible
	for lane_idx in range(3):
		lane_has_alive = any(c.alive and c.collected_at is None and c.lane_index == lane_idx for c in collectibles)
		if lane_has_alive:
			continue
		# choose a platform in the same lane and current surface if available
		lane_platforms = [p for p in platforms if p.lane_index == lane_idx and p.side == current_surface]
		if lane_platforms:
			ref_p = min(lane_platforms, key=lambda p: p.z)  # furthest forward
			ref_forward = ref_p.z
			side = ref_p.side
		else:
			# fallback: any platform current surface, else any platform
			cands = [p for p in platforms if p.side == current_surface] or platforms
			ref_p = min(cands, key=lambda p: p.z)
			ref_forward = ref_p.z
			side = ref_p.side
		target_z = ref_forward - random.uniform(orb_spawn_min_gap * 0.6, orb_spawn_max_gap * 0.9)
		coin_type = "trap" if random.random() < 0.12 else "normal"
		collectibles.append(Coin(lane_idx, side, target_z, coin_type=coin_type))


def detect_collision():
	# Player is at z=0; collide if same lane and near z
	if cheat_active or invisibility_active or shield_active:
		return False
	
	player_x = LANE_X[current_lane_index]
	# Enhanced collision detection for different obstacle types
	for obs in obstacles:
		# Only collide with obstacles on the current surface
		if obs.get("side", "Floor") != current_surface:
			continue
			
		otype = obs.get("type", "cube")
		collision_distance = 0.8
		
		# Adjust collision distance for different obstacle types
		if otype in ["moving_spike", "rotating_blade"]:
			collision_distance = 1.0  # Slightly larger for moving obstacles
		elif otype == "electric_wall":
			collision_distance = 0.9
		
		obs_x = obs["x"]
		# For moving spikes, use current position
		if otype == "moving_spike":
			obs_x = obs.get("x", obs["x"])  # x is updated in update_dynamic_obstacles
			
		if abs(obs_x - player_x) < collision_distance and (player_z_offset - collision_distance) <= obs["z"] <= (player_z_offset + collision_distance):
			return True
	return False


def display():
	# Handle different game states
	if game_state == "welcome":
		draw_welcome_screen()
		return
	elif game_state == "theme_selection":
		draw_theme_selection_screen()
		return
	elif game_state == "tutorial":
		draw_tutorial_screen()
		return
	
	# Main game display (game_state == "playing")
	# Set background clear color per theme (city uses sky)
	if current_theme == 'city':
		glClearColor(0.53, 0.81, 0.98, 1.0)
	else:
		glClearColor(0.1, 0.12, 0.16, 1.0)
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glLoadIdentity()
	# Camera: slightly above ground, looking forward along -Z
	gluLookAt(0.0, 2.0, 6.0,  0.0, 0.0, -10.0,  0.0, 1.0, 0.0)
	# Apply roll around Z-axis
	glRotatef(camera_roll_deg, 0.0, 0.0, 1.0)

	# Sky layer (behind gameplay): stars/moon/sun/clouds/rain/ufos
	flags = _theme_celestial_flags()
	if celestial_fade > 0.01:
		# Stars first
		if flags["stars"]:
			draw_stars()
		# Then sun/moon (exclusive typical)
		if flags["sun"]:
			draw_sun()
		elif flags["moon"]:
			draw_moon()
		# Then clouds
		if current_occasion in ('day', 'day_rain'):
			draw_clouds()
		# Then rain overlay
		if current_occasion in ('day_rain', 'night_rain'):
			draw_rain()
		# Then comets
		if flags["comets"]:
			draw_comet()
		# Then UFOs if selected
		if current_occasion == 'ufo':
			draw_ufos()

	draw_ground_and_lanes()
	# Draw platforms before player so player appears on top
	for p in platforms:
		# Only draw current-surface items to match the obstacle visibility rule
		if p.side == current_surface:
			p.draw()
	# Draw collectibles on current surface
	for c in collectibles:
		if c.side == current_surface:
			c.draw()
	# Draw bullets before player so they appear in front of scenery
	if bullets:
		glPushMatrix()
		glColor3f(1.0, 0.95, 0.2)
		for b in bullets:
			if b.get("alive", True) and b.get("side", current_surface) == current_surface:
				glPushMatrix()
				yb = -0.25 if current_surface == "Floor" else 0.25
				glTranslatef(LANE_X[b["lane"]], yb, b["z"])
				glScalef(0.15, 0.15, 0.4)
				draw_cube(1.0)
				glPopMatrix()
		glPopMatrix()

	draw_player()
	draw_obstacles()

	# HUD
	# Theme selection overlay (in-game overlay kept as fallback if selection window wasn't used)
	if theme_selection_active and current_theme is None and not is_game_over and selection_window_id is None:
		draw_text_2d(width * 0.5 - 160, height * 0.8, "Select Theme: 1) City  2) Jungle  3) Space")
		draw_text_2d(width * 0.5 - 220, height * 0.76, "City: roads/buildings  Jungle: ruins/vines  Space: station/drones")
		
	# Score bottom-left with orbs and cheat indicator
	cheat_label = " [CHEAT]" if cheat_active else ""
	abilities_text = ""
	if invisibility_active:
		abilities_text += " [INVIS]"
	if shield_active:
		abilities_text += " [SHIELD]"
	if auto_flip_safety_active:
		abilities_text += " [AUTO-FLIP]"
	if easy_path_active:
		abilities_text += " [EASY PATH]"
	if inverted_controls_active:
		abilities_text += " [INVERTED]"
	if random_flip_active:
		abilities_text += " [RANDOM FLIP]"
		
	draw_text_2d(12, height - 28, f"Score: {int(score)}  High: {int(high_score)}  Orbs: {orbs_collected}{cheat_label}{abilities_text}")
	
	# Show combo streak bonus
	if combo_display_time > 0:
		draw_text_2d(width * 0.5 - 100, height * 0.3, f"COMBO BONUS! +10 Orbs", color=(1.0, 0.8, 0.1))
		
	# Show current wall break streak
	if wall_break_streak > 0:
		draw_text_2d(12, height - 76, f"Wall Break Streak: {wall_break_streak}/{streak_bonus_threshold}", color=(0.8, 1.0, 0.8))
	
	# Show ability prompts when enough orbs are collected
	if not is_game_over:
		prompt_y = height - 52
		if orbs_collected >= 10 and not cheat_active:
			draw_text_2d(12, prompt_y, "C - Cheat Mode (10 orbs)", color=(0.1, 1.0, 0.1))
			prompt_y -= 20
		if orbs_collected >= easy_path_cost and not easy_path_active:
			draw_text_2d(12, prompt_y, f"E - Easy Path ({easy_path_cost} orbs)", color=(0.1, 0.8, 1.0))
			prompt_y -= 20
		if orbs_collected >= 5 and not invisibility_active:
			draw_text_2d(12, prompt_y, "I - Invisibility (5 orbs)", color=(0.8, 0.8, 1.0))
			prompt_y -= 20
		if orbs_collected >= 10 and not shield_active:
			draw_text_2d(12, prompt_y, "H - Shield (10 orbs)", color=(1.0, 0.8, 0.1))
			prompt_y -= 20
		if orbs_collected >= 8 and not auto_flip_safety_active:
			draw_text_2d(12, prompt_y, "T - Auto-Flip Safety (8 orbs)", color=(0.8, 1.0, 0.8))
			
	# Mode top-right
	mode_text = f"Mode: {current_difficulty_mode}"
	# shift a bit further left for visibility
	mx = width - (len(mode_text) * 9) - 64  # rough width estimate for placement
	# colorize by mode
	mode_color = (1.0, 1.0, 1.0)
	if current_difficulty_mode == "MEDIUM":
		mode_color = (1.0, 0.9, 0.2)
	elif current_difficulty_mode == "HARD":
		mode_color = (1.0, 0.25, 0.25)
	draw_text_2d(mx, height - 24, mode_text, color=mode_color)
	if is_game_over:
		if revive_available and waiting_for_revive_choice:
			draw_text_2d(width * 0.5 - 180, height * 0.52, "Game Over - Revive for 15 orbs? [Y/N]")
			# show orb count below
			draw_text_2d(width * 0.5 - 80, height * 0.5 - 22, f"Orbs: {orbs_collected}")
		else:
			draw_text_2d(width * 0.5 - 100, height * 0.5, "Game Over - Press R to restart")

	# Draw wall debris particles on top
	if wall_debris:
		for p in wall_debris:
			glPushMatrix()
			glTranslatef(p["pos"][0], p["pos"][1], p["pos"][2])
			glColor3f(0.85, 0.85, 0.9)
			s = p["size"]
			glScalef(s, s, s)
			draw_cube(1.0)
			glPopMatrix()

	glutSwapBuffers()


def update():
	global last_time, obstacles, score, is_game_over, high_score, camera_roll_deg, platforms, difficulty_factor, forward_speed, current_difficulty_mode, spawn_cap_per_frame, collectibles, orbs_collected, cheat_active, cheat_until_ts, revive_available, waiting_for_revive_choice, bullets, wall_debris
	now = time.time()
	if last_time is None:
		last_time = now
		dt = 0.0
	else:
		dt = min(0.05, now - last_time)
		last_time = now

	# Always update celestials for visual effects in all states
	update_celestials(dt, now)
	
	# Only run game logic during playing state
	if game_state == "playing" and not is_game_over:
		# Update abilities and power-ups
		update_abilities(dt, now)
		
		# Update combo streak system
		update_combo_streak(dt)
		
		# Auto-flip safety check
		check_auto_flip_safety()
		
		# Expire cheat mode if time elapsed
		if cheat_active and now >= cheat_until_ts:
			cheat_active = False
			
		# Update dynamic obstacles (moving spikes, rotating blades, etc.)
		update_dynamic_obstacles(dt)
		
		# Difficulty scaling: discrete modes + continuous factor
		prev_mode = current_difficulty_mode
		if score >= 400:
			current_difficulty_mode = "HARD"
		elif score >= 200:
			current_difficulty_mode = "MEDIUM"
		else:
			current_difficulty_mode = "EASY"
		# Continuous factor still ramps to smooth out transitions
		difficulty_factor = 1.0 + (score / 250.0)
		difficulty_factor = min(difficulty_factor, 6.0)
		# Update celestial systems (twinkle, comets, fade)
		update_celestials(dt, now)
		# Adjust speed and per-frame spawn cap by mode
		if current_difficulty_mode == "EASY":
			spawn_cap_per_frame = 1
			speed_scale = 1.00
		elif current_difficulty_mode == "MEDIUM":
			spawn_cap_per_frame = 3
			speed_scale = 1.35
		else:  # HARD
			spawn_cap_per_frame = 5
			speed_scale = 1.80
		# Blend base speed with difficulty factor and mode scale; clamp
		forward_speed = base_forward_speed * min(3.2, (1.0 + 0.18 * (difficulty_factor - 1.0)) * speed_scale)
		
		# Move obstacles towards the player (increase z toward 0)
		for obs in obstacles:
			obs["z"] += forward_speed * dt
		# Remove obstacles that passed the player
		obstacles = [o for o in obstacles if o["z"] < 2.0]
		# Spawn more ahead
		try_spawn_obstacles()

		# Update platforms (movement + break timers/fragments)
		for p in platforms:
			p.update(dt)
		# Remove platforms well past the player
		platforms = [p for p in platforms if not p.is_past_player() or (hasattr(p, 'fragments') and p.fragments)]
		# Spawn more platforms
		try_spawn_platforms()

		# Update collectibles
		for c in collectibles:
			c.update(dt)
		# Remove collected or passed collectibles
		collectibles = [c for c in collectibles if not c.is_past_player()]
		# Spawn more collectibles ahead
		try_spawn_collectibles()

		# Update car fire effect particles
		update_car_fire_effect(dt)

		# Update bullets
		if bullets:
			for b in bullets:
				if not b.get("alive", True):
					continue
				b["z"] -= bullet_speed * dt
				if b["z"] < -200.0:
					b["alive"] = False
			bullets = [b for b in bullets if b.get("alive", True)]

		# Bullet vs wall collision with enhanced wall breaking logic
		if bullets and obstacles:
			remaining_obs = []
			for obs in obstacles:
				otype = obs.get("type")
				if obs.get("side", "Floor") != current_surface:
					remaining_obs.append(obs)
					continue
				hit_remove_obs = False
				for b in bullets:
					if not b.get("alive", True):
						continue
					if b["lane"] != LANE_X.index(obs["x"]):
						continue
					if abs(b["z"] - obs["z"]) <= 0.6:
						b["alive"] = False
						# Enhanced wall breaking: only walls and electric walls can be destroyed
						if otype in ["wall", "electric_wall"]:
							spawn_wall_debris(obs["x"], (-0.25) if current_surface == "Floor" else 0.25, obs["z"])
							award_streak_bonus()  # Award streak bonus for wall breaks
							hit_remove_obs = True
						break
				if not hit_remove_obs:
					remaining_obs.append(obs)
			obstacles = remaining_obs
			bullets = [b for b in bullets if b.get("alive", True)]

		# Update wall debris
		if wall_debris:
			gravity = 7.0 * (1.0 if current_surface == "Ceiling" else -1.0)
			for p in wall_debris:
				p["vel"][1] += gravity * dt
				p["pos"][0] += p["vel"][0] * dt
				p["pos"][1] += p["vel"][1] * dt
				p["pos"][2] += p["vel"][2] * dt
				p["life"] -= dt
			wall_debris[:] = [p for p in wall_debris if p["life"] > 0]

		# Step detection: if player overlaps a platform on current surface, trigger break if breakable
		player_x = LANE_X[current_lane_index]
		# player z is offset by player_z_offset; consider small longitudinal tolerance
		for p in platforms:
			if p.side != current_surface:
				continue
			if not p.collider_enabled:
				continue
			x0, x1, z0, z1 = p.aabb()
			if x0 <= player_x <= x1 and (z0 <= player_z_offset <= z1 or abs(player_z_offset - z0) <= 0.3 or abs(player_z_offset - z1) <= 0.3):
				# Stepped on the platform
				if isinstance(p, BreakablePlatform):
					p.on_player_step()
					# If it immediately breaks (very small delay), player should fall -> game over
					# We keep gameplay simple: when collider disables and player is on it, mark game over
					if not p.collider_enabled:
						is_game_over = True

		# If a breakable platform finished breaking under the player this frame, end game
		if not is_game_over:
			for p in platforms:
				if isinstance(p, BreakablePlatform) and not p.collider_enabled and p.side == current_surface:
					x0, x1, z0, z1 = p.aabb()
					if x0 <= player_x <= x1 and z0 <= player_z_offset + 0.1 and z1 >= player_z_offset - 0.1:
						is_game_over = True
						break

		# Collectible collection: overlap with player
		if not is_game_over:
			for c in collectibles:
				if (not c.alive and c.collected_at is None) or c.side != current_surface:
					continue
				x = LANE_X[current_lane_index]
				if abs(LANE_X[c.lane_index] - x) <= 0.6 and abs(c.z - player_z_offset) <= 0.6:
					if isinstance(c, Coin) and c.coin_type == "trap":
						c.collect()
						trigger_car_fire_effect()
						orbs_collected = max(0, orbs_collected - 1)
					else:
						c.collect()
						orbs_collected += 1
						score += 10

		# Ease camera roll toward target
		diff = target_roll_deg - camera_roll_deg
		max_step = roll_speed_deg_per_sec * dt
		if abs(diff) <= max_step:
			camera_roll_deg = target_roll_deg
		else:
			camera_roll_deg += max_step if diff > 0 else -max_step
		# Collision
		if detect_collision():
			# Trigger game over; if orbs >= 15 provide revive option
			is_game_over = True
			revive_available = orbs_collected >= 15
			waiting_for_revive_choice = revive_available
			if score > high_score:
				high_score = score
		else:
			# Increase score by distance
			score += forward_speed * dt

	glutPostRedisplay()


def special_keys(key, x, y):
	global current_lane_index, current_surface
	# Apply inverted controls if active
	if inverted_controls_active:
		if current_surface == "Floor":
			# Invert controls for floor when power-down is active
			if key == GLUT_KEY_LEFT:
				current_lane_index = min(2, current_lane_index + 1)
			elif key == GLUT_KEY_RIGHT:
				current_lane_index = max(0, current_lane_index - 1)
		else:
			# Normal ceiling controls (already inverted) become double-inverted (normal)
			if key == GLUT_KEY_LEFT:
				current_lane_index = max(0, current_lane_index - 1)
			elif key == GLUT_KEY_RIGHT:
				current_lane_index = min(2, current_lane_index + 1)
	else:
		# Normal controls
		if current_surface == "Ceiling":
			# Invert controls to match screen orientation when rolled 180°
			if key == GLUT_KEY_LEFT:
				current_lane_index = min(2, current_lane_index + 1)
			elif key == GLUT_KEY_RIGHT:
				current_lane_index = max(0, current_lane_index - 1)
		else:
			if key == GLUT_KEY_LEFT:
				current_lane_index = max(0, current_lane_index - 1)
			elif key == GLUT_KEY_RIGHT:
				current_lane_index = min(2, current_lane_index + 1)
	glutPostRedisplay()


def keyboard(key, x, y):
	global is_game_over, current_surface, target_roll_deg, player_z_offset, cheat_active, cheat_until_ts, orbs_collected, revive_available, waiting_for_revive_choice, current_theme, theme_selection_active, current_occasion, bullets, _last_bullet_time, game_state, tutorial_step
	key = key.decode("utf-8") if isinstance(key, bytes) else key
	
	# Handle different game states
	if game_state == "welcome":
		if key == "\r" or key == "\n":  # Enter key
			advance_game_state()
		elif key in ("q", "Q", "\x1b"):
			glutLeaveMainLoop() if hasattr(GLUT, 'glutLeaveMainLoop') else exit(0)
		return
		
	elif game_state == "theme_selection":
		if key == "1":
			current_theme = 'city'
			advance_game_state()
		elif key == "2":
			current_theme = 'jungle'
			advance_game_state()
		elif key == "3":
			current_theme = 'space'
			advance_game_state()
		elif key in ("q", "Q", "\x1b"):
			glutLeaveMainLoop() if hasattr(GLUT, 'glutLeaveMainLoop') else exit(0)
		return
		
	elif game_state == "tutorial":
		if key == " ":  # Space - next tutorial step
			if tutorial_step < tutorial_max_steps - 1:
				tutorial_step += 1
			else:
				advance_game_state()  # Start the game
		elif key == "\b":  # Backspace - previous tutorial step
			go_back_tutorial()
		elif key == "\r" or key == "\n":  # Enter - start game (from last tutorial step)
			if tutorial_step == tutorial_max_steps - 1:
				advance_game_state()
		elif key in ("q", "Q", "\x1b"):
			glutLeaveMainLoop() if hasattr(GLUT, 'glutLeaveMainLoop') else exit(0)
		return
	
	# Main game controls (game_state == "playing")
	if key in ("q", "Q", "\x1b"):
		glutLeaveMainLoop() if hasattr(GLUT, 'glutLeaveMainLoop') else exit(0)
	elif key in ("r", "R"):
		# Reset to welcome screen instead of directly restarting
		game_state = "welcome"
		reset_game()
	elif key in ("a", "A") and not is_game_over:
		special_keys(GLUT_KEY_LEFT, 0, 0)
	elif key in ("d", "D") and not is_game_over:
		special_keys(GLUT_KEY_RIGHT, 0, 0)
	elif key == " " and not is_game_over:
		# Toggle surface; set target roll accordingly
		if current_surface == "Floor":
			current_surface = "Ceiling"
			target_roll_deg = 180.0
		else:
			current_surface = "Floor"
			target_roll_deg = 0.0
		# Grant brief invincibility during flip (0.5s)
		cheat_active = True
		cheat_until_ts = max(cheat_until_ts, time.time() + 1.0)
	elif key in ("c", "C") and not is_game_over:
		# Activate cheat mode if we have >= 10 orbs; costs 10, lasts 3s
		if orbs_collected >= 10 and not cheat_active:
			orbs_collected -= 10
			cheat_active = True
			cheat_until_ts = time.time() + 3.0
	elif key in ("e", "E") and not is_game_over:
		# Activate easy path mode
		activate_easy_path()
	elif key in ("i", "I") and not is_game_over:
		# Activate invisibility
		activate_ability("invisibility")
	elif key in ("h", "H") and not is_game_over:
		# Activate shield
		activate_ability("shield")
	elif key in ("t", "T") and not is_game_over:
		# Activate auto-flip safety
		activate_ability("auto_flip_safety")
	elif key in ("p", "P") and not is_game_over:
		# Activate inverted controls (power-down)
		activate_ability("inverted_controls")
	elif key in ("o", "O") and not is_game_over:
		# Activate random flip (power-down)
		activate_ability("random_flip")
	elif key in ("f", "F") and not is_game_over:
		# Fire bullet with simple cooldown
		fire_bullet()
	elif key in ("w", "W") and not is_game_over:
		# Move forward along -Z (toward camera)
		player_z_offset = max(player_z_min, player_z_offset - player_z_step)
	elif key in ("s", "S") and not is_game_over:
		# Move backward along +Z
		player_z_offset = min(player_z_max, player_z_offset + player_z_step)
	elif not is_game_over:
		# Occasion Change Mode (keys 5–9) only changes sky layer, not ground
		if key == "5":
			current_occasion = 'night'
			init_celestials_for_theme()
		elif key == "6":
			current_occasion = 'day'
			init_celestials_for_theme()
		elif key == "7":
			current_occasion = 'night_rain'
			init_celestials_for_theme()
		elif key == "8":
			current_occasion = 'day_rain'
			init_celestials_for_theme()
		elif key == "9":
			current_occasion = 'ufo'
			init_celestials_for_theme()
	elif is_game_over and waiting_for_revive_choice:
		# Handle revive prompts
		if key in ("y", "Y") and revive_available and orbs_collected >= 15:
			# Consume orbs and revive
			orbs_collected -= 15
			is_game_over = False
			revive_available = False
			waiting_for_revive_choice = False
			# Grant brief invulnerability on revive
			cheat_active = True
			cheat_until_ts = time.time() + 3.0
			# Clear obstacles too close to player to avoid instant re-death
			near_clear_z = 4.0
			obstacles[:] = [o for o in obstacles if o["z"] < -near_clear_z or o["z"] > near_clear_z]
			# Also clear breaking platforms immediately underfoot on current surface
			for p in platforms:
				if p.side == current_surface:
					p.collider_enabled = True
		elif key in ("n", "N"):
			# Decline revive; stay in game over
			revive_available = False
			waiting_for_revive_choice = False



def reshape(w, h):
	global width, height
	width, height = max(1, w), max(1, h)
	glViewport(0, 0, width, height)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	gluPerspective(60.0, width / float(height), 0.1, 300.0)
	glMatrixMode(GL_MODELVIEW)


def main():
	glutInit()
	glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
	# Create main game window
	glutInitWindowSize(width, height)
	main_window_id = glutCreateWindow(b"Gravity Flip Runner - Enhanced Edition")
	
	init()
	
	glutDisplayFunc(display)
	glutIdleFunc(update)  # Use update for idle to handle game logic
	glutReshapeFunc(reshape)
	glutKeyboardFunc(keyboard)
	glutSpecialFunc(special_keys)
	
	# Mouse: left-button fire (only works during gameplay)
	def _mouse(btn, state, mx, my):
		if btn == GLUT_LEFT_BUTTON and state == GLUT_DOWN and game_state == "playing" and not is_game_over:
			fire_bullet()
	glutMouseFunc(_mouse)
	
	glutMainLoop()


if __name__ == "__main__":
	main()


