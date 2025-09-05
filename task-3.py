from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

if not hasattr(math, 'tau'):
    math.tau = 2 * math.pi

ARENA_HALF = 25.0
GRID_STEP = 2.5
WALL_HEIGHT = 4.0
PLAYER_RADIUS = 1.0
ENEMY_RADIUS = 0.8
ENEMY_COUNT = 5
BULLET_SPEED = 25.0
ENEMY_SPEED = 4.0
PLAYER_SPEED = 8.0
GUN_LENGTH = 2.0
BULLET_SIZE = 0.25
COLLISION_PLAYER_ENEMY = 1.4
COLLISION_BULLET_ENEMY = 1.0
MAX_MISSED = 10
START_LIFE = 5

class Bullet:
    def __init__(self, x, z, yaw):
        self.x = x
        self.z = z
        self.yaw = yaw
        self.dead = False
        self.color_phase = random.uniform(0, math.tau)

    def update(self, dt):
        rad = math.radians(self.yaw)
        self.x += math.cos(rad) * BULLET_SPEED * dt
        self.z += math.sin(rad) * BULLET_SPEED * dt
        self.color_phase = (self.color_phase + 5.0 * dt) % math.tau
        if abs(self.x) > ARENA_HALF + 1 or abs(self.z) > ARENA_HALF + 1:
            self.dead = True

    def get_color(self):
        r = 0.5 + 0.5 * math.sin(self.color_phase)
        g = 0.5 + 0.5 * math.sin(self.color_phase + 2.094)
        b = 0.5 + 0.5 * math.sin(self.color_phase + 4.189)
        return (r, g, b)

class Enemy:
    def __init__(self):
        self.respawn()
        self.scale_phase = random.uniform(0, math.tau)
        self.base_color = (
            random.uniform(0.7, 1.0),
            random.uniform(0.3, 0.8),
            random.uniform(0.1, 0.6)
        )

    def respawn(self):
        ang = random.uniform(0, math.tau)
        r = random.uniform(12.0, 20.0)
        self.x = math.cos(ang) * r
        self.z = math.sin(ang) * r

    def update(self, dt, player_x, player_z):
        dx = player_x - self.x
        dz = player_z - self.z
        dist = math.hypot(dx, dz) + 1e-6
        ux = dx / dist
        uz = dz / dist
        self.x += ux * ENEMY_SPEED * dt
        self.z += uz * ENEMY_SPEED * dt
        self.scale_phase = (self.scale_phase + 2.0 * dt) % math.tau

    def scale_amount(self):
        return 0.85 + 0.15 * (0.5 * (1.0 + math.sin(self.scale_phase)))

    def get_color(self):
        pulse = 0.3 + 0.7 * (0.5 * (1.0 + math.sin(self.scale_phase * 2)))
        r = self.base_color[0] * pulse
        g = self.base_color[1] * pulse
        b = self.base_color[2] * pulse
        return (r, g, b)

class Player:
    def __init__(self):
        self.x = 0.0
        self.z = 0.0
        self.yaw = 0.0
        self.life = START_LIFE
        self.score = 0
        self.missed = 0
        self.game_over = False
        self.cheat_mode = False
        self.auto_cam_follow = False
        self.color_phase = 0.0

    def update_color(self, dt):
        self.color_phase = (self.color_phase + 1.0 * dt) % math.tau

    def get_color(self):
        if self.cheat_mode:
            r = 0.5 + 0.5 * math.sin(self.color_phase)
            g = 0.5 + 0.5 * math.sin(self.color_phase + 2.094)
            b = 0.5 + 0.5 * math.sin(self.color_phase + 4.189)
            return (r, g, b)
        else:
            return (0.2, 0.6, 1.0)

class Camera:
    def __init__(self):
        self.mode_first_person = False
        self.orbit_angle = 45.0
        self.height = 15.0
        self.distance = 40.0

    def apply(self, player):
        if self.mode_first_person:
            rad = math.radians(player.yaw)
            eye_x = player.x + math.cos(rad) * (GUN_LENGTH * 0.6)
            eye_y = 1.4
            eye_z = player.z + math.sin(rad) * (GUN_LENGTH * 0.6)
            
            if player.cheat_mode and player.auto_cam_follow:
                eye_y = 2.0
                eye_x -= math.cos(rad) * 0.5
                eye_z -= math.sin(rad) * 0.5
            
            ctr_x = eye_x + math.cos(rad)
            ctr_y = eye_y
            ctr_z = eye_z + math.sin(rad)
            gluLookAt(eye_x, eye_y, eye_z, ctr_x, ctr_y, ctr_z, 0, 1, 0)
        else:
            ang = math.radians(self.orbit_angle)
            eye_x = math.cos(ang) * self.distance + player.x
            eye_z = math.sin(ang) * self.distance + player.z
            eye_y = self.height
            gluLookAt(eye_x, eye_y, eye_z, player.x, 0.8, player.z, 0, 1, 0)

player = Player()
cam = Camera()
bullets = []
enemies = []

for i in range(ENEMY_COUNT):
    enemies.append(Enemy())

keys_down = set()
last_time = None

def draw_grid_and_walls():
    # Chessboard Grid
    x_start = -int(ARENA_HALF)
    x_end = int(ARENA_HALF)
    z_start = -int(ARENA_HALF)
    z_end = int(ARENA_HALF)
    
    x = x_start
    while x < x_end:
        z = z_start
        while z < z_end:
            # Calculate chessboard pattern
            grid_x = int((x + ARENA_HALF) / GRID_STEP)
            grid_z = int((z + ARENA_HALF) / GRID_STEP)
            
            # Alternate colors like chessboard
            if (grid_x + grid_z) % 2 == 0:
                # Light purple squares
                glColor3f(0.8, 0.7, 1.0)
            else:
                # White squares
                glColor3f(1.0, 1.0, 1.0)
            
            glBegin(GL_QUADS)
            glVertex3f(x, 0, z)
            glVertex3f(x + GRID_STEP, 0, z)
            glVertex3f(x + GRID_STEP, 0, z + GRID_STEP)
            glVertex3f(x, 0, z + GRID_STEP)
            glEnd()
            z += GRID_STEP
        x += GRID_STEP

    # Walls
    wall_colors = [
        (0.8, 0.2, 0.2),  # Red
        (0.2, 0.8, 0.2),  # Green
        (0.2, 0.2, 0.8),  # Blue
        (0.8, 0.8, 0.2),  # Yellow
    ]
    
    wall_positions = [
        (-ARENA_HALF, -ARENA_HALF, ARENA_HALF, -ARENA_HALF),
        (ARENA_HALF, -ARENA_HALF, ARENA_HALF, ARENA_HALF),
        (-ARENA_HALF, ARENA_HALF, ARENA_HALF, ARENA_HALF),
        (-ARENA_HALF, -ARENA_HALF, -ARENA_HALF, ARENA_HALF),
    ]
    
    i = 0
    while i < len(wall_positions):
        x1, z1, x2, z2 = wall_positions[i]
        r, g, b = wall_colors[i]
        glColor3f(r, g, b)
        glBegin(GL_QUADS)
        glVertex3f(x1, 0, z1)
        glVertex3f(x2, 0, z2)
        glVertex3f(x2, WALL_HEIGHT, z2)
        glVertex3f(x1, WALL_HEIGHT, z1)
        glEnd()
        i += 1

def draw_cuboid(dx, dy, dz):
    glPushMatrix()
    glScalef(dx, dy, dz)
    
    glBegin(GL_QUADS)
    # Front face
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    
    # Back face
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(-0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(0.5, -0.5, -0.5)
    
    # Top face
    glVertex3f(-0.5, 0.5, -0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, -0.5)
    
    # Bottom face
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(-0.5, -0.5, 0.5)
    
    # Right face
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(0.5, -0.5, 0.5)
    
    # Left face
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, -0.5)
    glEnd()
    
    glPopMatrix()

def draw_cylinder(radius=0.2, height=1.0, slices=24):
    glPushMatrix()
    glTranslatef(0, height/2.0, 0)
    
    angle_step = 2 * math.pi / slices
    i = 0
    while i < slices:
        angle1 = i * angle_step
        angle2 = (i + 1) * angle_step
        
        x1 = radius * math.cos(angle1)
        z1 = radius * math.sin(angle1)
        x2 = radius * math.cos(angle2)
        z2 = radius * math.sin(angle2)
        
        # Side face
        glBegin(GL_QUADS)
        glVertex3f(x1, -height/2, z1)
        glVertex3f(x2, -height/2, z2)
        glVertex3f(x2, height/2, z2)
        glVertex3f(x1, height/2, z1)
        glEnd()
        
        # Top face
        glBegin(GL_TRIANGLES)
        glVertex3f(0, height/2, 0)
        glVertex3f(x1, height/2, z1)
        glVertex3f(x2, height/2, z2)
        glEnd()
        
        # Bottom face
        glBegin(GL_TRIANGLES)
        glVertex3f(0, -height/2, 0)
        glVertex3f(x2, -height/2, z2)
        glVertex3f(x1, -height/2, z1)
        glEnd()
        
        i += 1
    
    glPopMatrix()

def draw_sphere(radius=1.0, slices=16, stacks=16):
    i = 0
    while i < stacks:
        lat0 = math.pi * (-0.5 + float(i) / stacks)
        z0 = math.sin(lat0)
        zr0 = math.cos(lat0)
        
        lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
        z1 = math.sin(lat1)
        zr1 = math.cos(lat1)
        
        glBegin(GL_QUAD_STRIP)
        j = 0
        while j <= slices:
            lng = 2 * math.pi * float(j) / slices
            x = math.cos(lng)
            y = math.sin(lng)
            
            glVertex3f(x * zr0 * radius, y * zr0 * radius, z0 * radius)
            glVertex3f(x * zr1 * radius, y * zr1 * radius, z1 * radius)
            j += 1
        glEnd()
        i += 1

def draw_player(p):
    glPushMatrix()
    glTranslatef(p.x, 0, p.z)
    
    if p.game_over:
        glRotatef(90, 0, 0, 1)
        glTranslatef(0.0, PLAYER_RADIUS*0.2, 0.0)

    # Body
    r, g, b = p.get_color()
    glColor3f(r, g, b)
    glPushMatrix()
    glTranslatef(0, PLAYER_RADIUS, 0)
    draw_sphere(PLAYER_RADIUS, 24, 24)
    glPopMatrix()

    # Torso
    glColor3f(0.1, 0.4, 0.9)
    glPushMatrix()
    glTranslatef(0, 0.2, 0)
    draw_cylinder(0.35, 1.2)
    glPopMatrix()

    # Feet
    glColor3f(0.15, 0.15, 0.2)
    sx_values = [-1, 1]
    sx_index = 0
    while sx_index < len(sx_values):
        sx = sx_values[sx_index]
        glPushMatrix()
        glTranslatef(0.25*sx, 0.1, 0.2)
        draw_cuboid(0.35, 0.2, 0.6)
        glPopMatrix()
        sx_index += 1
    
    # Gun mount
    glPushMatrix()
    glRotatef(p.yaw, 0, 1, 0)

    # Gun base
    glColor3f(0.8, 0.2, 0.2)
    glPushMatrix()
    glTranslatef(0.0, 1.0, 0.0)
    draw_cylinder(0.15, 0.4)
    glPopMatrix()
    
    # Gun barrel
    glColor3f(0.9, 0.3, 0.3)
    glPushMatrix()
    glTranslatef(GUN_LENGTH/2.0, 1.15, 0.0)
    draw_cuboid(GUN_LENGTH, 0.15, 0.15)
    glPopMatrix()
    
    glPopMatrix()
    glPopMatrix()

def draw_enemy(e):
    glPushMatrix()
    glTranslatef(e.x, 0, e.z)
    s = e.scale_amount()
    glScalef(s, s, s)

    # Body
    r, g, b = e.get_color()
    glColor3f(r, g, b)
    glPushMatrix()
    glTranslatef(0, ENEMY_RADIUS, 0)
    draw_sphere(ENEMY_RADIUS, 20, 20)
    glPopMatrix()
    
    # Head
    head_r = r * 0.7
    head_g = g * 0.7
    head_b = b * 0.7
    glColor3f(head_r, head_g, head_b)
    glPushMatrix()
    glTranslatef(0, ENEMY_RADIUS*2.0, 0)
    draw_sphere(ENEMY_RADIUS*0.7, 20, 20)
    glPopMatrix()
    
    glPopMatrix()

def draw_bullet(b):
    glPushMatrix()
    glTranslatef(b.x, 0.9, b.z)
    glRotatef(b.yaw, 0, 1, 0)
    r, g, b_color = b.get_color()
    glColor3f(r, g, b_color)
    draw_cuboid(BULLET_SIZE, BULLET_SIZE, BULLET_SIZE)
    glPopMatrix()

def clamp(v, a, b):
    if v < a:
        return a
    if v > b:
        return b
    return v

def distance_xz(x1, z1, x2, z2):
    return math.hypot(x1-x2, z1-z2)

def enemy_in_sight(p, e, fov_deg=8.0, max_dist=18.0):
    dx = e.x - p.x
    dz = e.z - p.z
    dist = math.hypot(dx, dz)
    if dist > max_dist:
        return False
    ang_to_enemy = math.degrees(math.atan2(dz, dx))
    d = (ang_to_enemy - p.yaw + 180.0) % 360.0 - 180.0
    return abs(d) < (fov_deg * 0.5)

def reset_game():
    global player, bullets, enemies
    player = Player()
    bullets = []
    enemies = []
    i = 0
    while i < ENEMY_COUNT:
        enemies.append(Enemy())
        i += 1

def fire_bullet():
    global bullets
    if player.game_over:
        return
    rad = math.radians(player.yaw)
    start_x = player.x + math.cos(rad) * (GUN_LENGTH + 0.5)
    start_z = player.z + math.sin(rad) * (GUN_LENGTH + 0.5)
    bullets.append(Bullet(start_x, start_z, player.yaw))

def update(dt):
    global bullets, enemies
    if dt <= 0:
        return
        
    if player.game_over:
        return

    player.update_color(dt)

    # Player movement
    move_dir = 0.0
    if b"w" in keys_down:
        move_dir += 1.0
    if b"s" in keys_down:
        move_dir -= 1.0

    yaw_dir = 0.0
    if b"a" in keys_down:
        yaw_dir += 1.0
    if b"d" in keys_down:
        yaw_dir -= 1.0

    player.yaw = (player.yaw + yaw_dir * 120.0 * dt) % 360.0
    if move_dir != 0.0:
        rad = math.radians(player.yaw)
        player.x += math.cos(rad) * (PLAYER_SPEED * move_dir * dt)
        player.z += math.sin(rad) * (PLAYER_SPEED * move_dir * dt)
        player.x = clamp(player.x, -ARENA_HALF+1.0, ARENA_HALF-1.0)
        player.z = clamp(player.z, -ARENA_HALF+1.0, ARENA_HALF-1.0)

    # Cheat mode
    if player.cheat_mode:
        player.yaw = (player.yaw + 120.0 * dt) % 360.0
        i = 0
        while i < len(enemies):
            e = enemies[i]
            if enemy_in_sight(player, e):
                if random.random() < 0.15:
                    fire_bullet()
                    break
            i += 1

    # Update bullets
    i = 0
    while i < len(bullets):
        bullets[i].update(dt)
        i += 1

    # Check bullet-enemy collisions
    i = 0
    while i < len(bullets):
        b = bullets[i]
        if b.dead:
            i += 1
            continue
        j = 0
        while j < len(enemies):
            e = enemies[j]
            if distance_xz(b.x, b.z, e.x, e.z) < COLLISION_BULLET_ENEMY:
                b.dead = True
                player.score += 1
                e.respawn()
                break
            j += 1
        i += 1

    # Count missed bullets and remove dead
    remaining = []
    i = 0
    while i < len(bullets):
        b = bullets[i]
        if b.dead:
            if abs(b.x) > ARENA_HALF + 0.5 or abs(b.z) > ARENA_HALF + 0.5:
                if not player.cheat_mode:
                    player.missed += 1
        else:
            remaining.append(b)
        i += 1
    bullets = remaining

    # Update enemies & check player collisions
    i = 0
    while i < len(enemies):
        e = enemies[i]
        e.update(dt, player.x, player.z)
        if distance_xz(player.x, player.z, e.x, e.z) < COLLISION_PLAYER_ENEMY:
            if not player.cheat_mode:
                player.life -= 1
                e.respawn()
                if player.life <= 0:
                    player.life = 0
        i += 1

    # Game over conditions
    if (player.life <= 0 or player.missed >= MAX_MISSED) and not player.cheat_mode:
        player.game_over = True

def draw_text_2d(x, y, s):
    glRasterPos2f(x, y)
    i = 0
    while i < len(s):
        ch = s[i]
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
        i += 1

def draw_hud():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(1, 1, 1)
    draw_text_2d(10, 570, f"Life: {player.life}   Score: {player.score}   Missed: {player.missed}/{MAX_MISSED}")
    
    if cam.mode_first_person:
        mode = "FP"
    else:
        mode = "TP"
    
    if player.cheat_mode:
        cheat = "ON"
    else:
        cheat = "OFF"
    
    if player.auto_cam_follow:
        auto_cam = "ON"
    else:
        auto_cam = "OFF"
    
    draw_text_2d(10, 545, f"Cam: {mode}   Cheat: {cheat}   AutoCam: {auto_cam}")
    draw_text_2d(10, 520, "(W/S move, A/D rotate, LMB fire, RMB cam mode, C cheat, V auto-cam)")

    if player.game_over:
        glColor3f(1.0, 0.3, 0.3)
        draw_text_2d(270, 310, "GAME OVER")
        glColor3f(1.0, 1.0, 1.0)
        draw_text_2d(220, 280, "Press R to Restart")

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, 800/600, 0.1, 200.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    cam.apply(player)

    draw_grid_and_walls()

    i = 0
    while i < len(enemies):
        draw_enemy(enemies[i])
        i += 1

    draw_player(player)

    i = 0
    while i < len(bullets):
        draw_bullet(bullets[i])
        i += 1

    draw_hud()
    
    glutSwapBuffers()

def idle():
    global last_time
    now = time.time()
    if last_time is None:
        last_time = now
    dt = now - last_time
    last_time = now

    update(dt)
    
    glutPostRedisplay()

def reshape(w, h):
    glViewport(0, 0, w, h)

def keyboard_down(key, x, y):
    global keys_down
    if key == b"\x1b":
        import sys
        sys.exit(0)
    if key in (b"w", b"a", b"s", b"d"):
        keys_down.add(key)
    elif key in (b"c", b"C"):
        if not player.game_over:
            player.cheat_mode = not player.cheat_mode
            print(f"Cheat mode: {'ON' if player.cheat_mode else 'OFF'}")
            if not player.cheat_mode:
                player.auto_cam_follow = False
    elif key in (b"v", b"V"):
        if not player.game_over and player.cheat_mode:
            player.auto_cam_follow = not player.auto_cam_follow
            print(f"Auto camera follow: {'ON' if player.auto_cam_follow else 'OFF'}")
        elif not player.cheat_mode:
            print("Auto camera follow only works when cheat mode is ON")
    elif key in (b"r", b"R"):
        reset_game()

def keyboard_up(key, x, y):
    if key in keys_down:
        keys_down.remove(key)

def special_keys(key, x, y):
    if player.game_over:
        return
    if key == GLUT_KEY_LEFT:
        cam.orbit_angle = (cam.orbit_angle - 3.0) % 360.0
    elif key == GLUT_KEY_RIGHT:
        cam.orbit_angle = (cam.orbit_angle + 3.0) % 360.0
    elif key == GLUT_KEY_UP:
        cam.height = clamp(cam.height + 0.6, 3.0, 45.0)
    elif key == GLUT_KEY_DOWN:
        cam.height = clamp(cam.height - 0.6, 3.0, 45.0)

def mouse(btn, state, x, y):
    if btn == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if not player.game_over:
            fire_bullet()
    elif btn == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        cam.mode_first_person = not cam.mode_first_person

def init_gl():
    glClearColor(0.05, 0.07, 0.1, 1)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_COLOR_MATERIAL)
    glShadeModel(GL_SMOOTH)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"Bullet Frenzy - CSE423 Lab 03")

    init_gl()

    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard_down)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_keys)
    glutMouseFunc(mouse)
    
    glutMainLoop()

if __name__ == "__main__":
    main()
