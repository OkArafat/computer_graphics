from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import OpenGL.GLUT as GLUT
import random
import time
import math


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

# Cheat mode
cheat_active = False
cheat_until_ts = 0.0

# Revive system
revive_available = False
waiting_for_revive_choice = False

# Theme system
current_theme = None  # 'city' | 'jungle' | 'space'
theme_selection_active = True
selection_window_id = None
main_window_id = None
selection_window_w = 1200
selection_window_h = 500

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
	is_game_over = False
	score = 0.0
	current_lane_index = 1
	obstacles = []
	seed_initial_obstacles()
	platforms = []
	seed_initial_platforms()
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
	# Reset difficulty and speed
	difficulty_factor = 1.0
	forward_speed = base_forward_speed
	current_difficulty_mode = "EASY"
	spawn_cap_per_frame = 1
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
		# Choose obstacle type by mode
		if current_difficulty_mode == "EASY":
			otype = choose_by_weights(get_theme_def()["obstacle_weights"]) if current_theme else "cube"
		elif current_difficulty_mode == "MEDIUM":
			# Favor traps in medium
			otype = choose_by_weights([("trap", 0.4)] + get_theme_def()["obstacle_weights"]) if current_theme else ("trap" if random.random() < 0.6 else "cube")
		else:  # HARD
			# Favor theme-specific hard obstacles
			weights = get_theme_def()["obstacle_weights"] if current_theme else [("ball", 0.45), ("trap", 0.35), ("cube", 0.2)]
			otype = choose_by_weights(weights)
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
		obstacles.append(obs)
		spawned += 1
		# Cap spawns per frame depending on mode
		if spawned >= spawn_cap_per_frame:
			break

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
		# Choose obstacle type by mode (same logic as above)
		if current_difficulty_mode == "EASY":
			otype = "cube"
		elif current_difficulty_mode == "MEDIUM":
			otype = "trap" if random.random() < 0.6 else "cube"
		else:
			roll = random.random()
			if roll < 0.45:
				otype = "ball"
			elif roll < 0.80:
				otype = "trap"
			else:
				otype = "cube"
		obs = {"x": LANE_X[lane], "z": target_z, "size": size, "side": side, "type": otype}
		if otype == "ball":
			obs["radius"] = random.uniform(0.6, 1.1)
		elif otype == "trap":
			obs["length"] = random.uniform(1.4, 2.2)
		obstacles.append(obs)


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
	if cheat_active:
		return False
	player_x = LANE_X[current_lane_index]
	# Platforms: if no platform underfoot on current surface and we previously stepped onto a breaking one, allow fall
	for obs in obstacles:
		# Only collide with obstacles on the current surface
		if obs.get("side", "Floor") != current_surface:
			continue
		if abs(obs["x"] - player_x) < 0.1 and (player_z_offset - 0.8) <= obs["z"] <= (player_z_offset + 0.8):
			return True
	return False


def display():
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
	draw_player()
	draw_obstacles()

	# HUD
	# Theme selection overlay (in-game overlay kept as fallback if selection window wasn't used)
	if theme_selection_active and current_theme is None and not is_game_over and selection_window_id is None:
		draw_text_2d(width * 0.5 - 160, height * 0.8, "Select Theme: 1) City  2) Jungle  3) Space")
		draw_text_2d(width * 0.5 - 220, height * 0.76, "City: roads/buildings  Jungle: ruins/vines  Space: station/drones")
	# Score bottom-left with orbs and cheat indicator
	cheat_label = " [CHEAT]" if cheat_active else ""
	draw_text_2d(12, height - 28, f"Score: {int(score)}  High: {int(high_score)}  Orbs: {orbs_collected}{cheat_label}")
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

	glutSwapBuffers()


def update():
	global last_time, obstacles, score, is_game_over, high_score, camera_roll_deg, platforms, difficulty_factor, forward_speed, current_difficulty_mode, spawn_cap_per_frame, collectibles, orbs_collected, cheat_active, cheat_until_ts, revive_available, waiting_for_revive_choice
	now = time.time()
	if last_time is None:
		last_time = now
		dt = 0.0
	else:
		dt = min(0.05, now - last_time)
		last_time = now

	if not is_game_over:
		# Expire cheat mode if time elapsed
		if cheat_active and now >= cheat_until_ts:
			cheat_active = False
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
	global is_game_over, current_surface, target_roll_deg, player_z_offset, cheat_active, cheat_until_ts, orbs_collected, revive_available, waiting_for_revive_choice, current_theme, theme_selection_active
	key = key.decode("utf-8") if isinstance(key, bytes) else key
	if key in ("q", "Q", "\x1b"):
		glutLeaveMainLoop() if hasattr(GLUT, 'glutLeaveMainLoop') else exit(0)
	elif key in ("r", "R"):
		# If we are waiting for revive choice, R behaves as normal restart
		reset_game()
		# Keep theme selection active after reset until chosen again
		theme_selection_active = True
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
	elif key in ("c", "C") and not is_game_over:
		# Activate cheat mode if we have >= 10 orbs; costs 10, lasts 3s
		if orbs_collected >= 10 and not cheat_active:
			orbs_collected -= 10
			cheat_active = True
			cheat_until_ts = time.time() + 3.0
	elif theme_selection_active and current_theme is None and not is_game_over:
		# Theme choices: 1,2,3
		if key == "1":
			current_theme = 'city'
			theme_selection_active = False
			# reseed obstacles to reflect theme immediately
			obstacles.clear()
			seed_initial_obstacles()
		elif key == "2":
			current_theme = 'jungle'
			theme_selection_active = False
			obstacles.clear()
			seed_initial_obstacles()
		elif key == "3":
			current_theme = 'space'
			theme_selection_active = False
			obstacles.clear()
			seed_initial_obstacles()
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
	elif key in ("w", "W") and not is_game_over:
		player_z_offset = max(player_z_min, player_z_offset - player_z_step)
	elif key in ("s", "S") and not is_game_over:
		player_z_offset = min(player_z_max, player_z_offset + player_z_step)


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
	# Create selection window first
	glutInitWindowSize(selection_window_w, selection_window_h)
	global selection_window_id, main_window_id
	selection_window_id = glutCreateWindow(b"Gravity Flip Racer - Select Theme")

	def selection_display():
		glClear(GL_COLOR_BUFFER_BIT)
		glLoadIdentity()
		# Gradient background (also set viewport to selection window size)
		glViewport(0, 0, selection_window_w, selection_window_h)
		_sel_draw_gradient_bg(selection_window_w, selection_window_h, (0.06, 0.07, 0.10), (0.02, 0.02, 0.03))
		# Animated glow phase
		phase = (time.time() * 0.9) % 1.0
		# Stylish big-font options (no cards)
		glDisable(GL_DEPTH_TEST)
		# Title
		shadow_col = (0.06, 0.06, 0.08)
		title_col = (0.95, 0.95, 1.0)
		
		draw_text(30, selection_window_h - 30, "Gravity Flip Racer", font=GLUT.GLUT_BITMAP_TIMES_ROMAN_24, color=title_col)
		# Subtitle
		sub_col = (0.85, 0.88, 0.95)
		draw_text(30, selection_window_h - 60, "Select a Theme:", font=GLUT.GLUT_BITMAP_HELVETICA_18, color=sub_col)
		# Options with subtle animated color
		anim = 0.7 + 0.3 * abs((phase*2.0) % 2.0 - 1.0)
		opt1_col = (anim, 0.85, 0.30)
		opt2_col = (0.55, 0.9*anim, 0.45)
		opt3_col = (0.55, 0.8, anim)
		draw_text(60, selection_window_h - 110, "1) City", font=GLUT.GLUT_BITMAP_TIMES_ROMAN_24, color=opt1_col)
		draw_text(60, selection_window_h - 150, "2) Jungle Ruins", font=GLUT.GLUT_BITMAP_TIMES_ROMAN_24, color=opt2_col)
		draw_text(60, selection_window_h - 190, "3) Space Station", font=GLUT.GLUT_BITMAP_TIMES_ROMAN_24, color=opt3_col)
		glEnable(GL_DEPTH_TEST)
		# Title and subtitle (ensure drawn in front of everything)
		glDisable(GL_DEPTH_TEST)
		glEnable(GL_DEPTH_TEST)
		glutSwapBuffers()

	def selection_keyboard(key, x, y):
		global current_theme, theme_selection_active, selection_window_id, main_window_id
		key = key.decode("utf-8") if isinstance(key, bytes) else key
		if key in ("1", "2", "3"):
			current_theme = 'city' if key == '1' else ('jungle' if key == '2' else 'space')
			theme_selection_active = False
			# Close selection window and open main window
			if selection_window_id is not None:
				try:
					glutDestroyWindow(selection_window_id)
				except Exception:
					pass
				selection_window_id = None
			# Create main game window
			glutInitWindowSize(width, height)
			main_window_id = glutCreateWindow(b"CSE423 - 3-Lane Endless Runner")
			init()
			reset_game()
			glutDisplayFunc(display)
			glutIdleFunc(update)
			glutReshapeFunc(reshape)
			glutKeyboardFunc(keyboard)
			glutSpecialFunc(special_keys)
		else:
			# Allow quitting from selection
			if key in ("q", "Q", "\x1b"):
				glutLeaveMainLoop() if hasattr(GLUT, 'glutLeaveMainLoop') else exit(0)

	# Setup selection window callbacks and idle to animate
	glutDisplayFunc(selection_display)
	glutKeyboardFunc(selection_keyboard)
	glutIdleFunc(selection_display)
	glutMainLoop()


if __name__ == "__main__":
	main()


