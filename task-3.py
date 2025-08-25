from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random

# Game state variables
class GameState:
    def __init__(self):
        self.player_life = 5
        self.game_score = 0
        self.bullets_missed = 0
        self.game_over = False
        self.cheat_mode = False
        self.cheat_vision = False
        self.camera_mode = "third_person"  # "third_person" or "first_person"
        self.player_pos = [0, 0, 0]
        self.player_rotation = 0
        self.camera_pos = [0, 500, 500]
        self.target_camera_pos = [0, 500, 500]  # for smooth interpolation
        self.camera_rotation = 0
        self.target_camera_rotation = 0  # for smooth interpolation
        self.camera_smooth_factor = 0.1  # interpolation speed
        self.frame_count = 0  # for performance monitoring
        self.bullets = []
        self.enemies = []
        self.enemy_spawn_timer = 0
        self.enemy_scale = 1.0
        self.enemy_scale_direction = 0.01
        self.hit_cooldown = 0  # frames remaining immune after a hit

# Global game state
game_state = GameState()

# reuse quadric objects to avoid recreating each draw call
GLOBAL_QUADRIC = gluNewQuadric()

# Performance optimization: batch rendering preparation
def prepare_batch_rendering():
    """Prepare OpenGL state for efficient batch rendering"""
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)  # backface culling for better performance
    glCullFace(GL_BACK)

# Constants
GRID_LENGTH = 600
BOUNDARY_HEIGHT = 100
BULLET_SPEED = 5
BULLET_MAX_RANGE = 800  # maximum distance bullets can travel
ENEMY_SPEED = 1
PLAYER_SPEED = 3
CAMERA_ROTATION_SPEED = 2
CAMERA_HEIGHT_SPEED = 10

# Collision constants
PLAYER_RADIUS = 25
ENEMY_RADIUS = 20
BULLET_HALF = 5

def init_game():
    """Initialize the game with enemies and reset state"""
    global game_state
    game_state.enemies = []
    game_state.bullets = []
    game_state.player_pos = [0, 0, 0]
    game_state.player_rotation = 0
    game_state.camera_pos = [0, 500, 500]
    game_state.camera_rotation = 0
    game_state.player_life = 5
    game_state.game_score = 0
    game_state.bullets_missed = 0
    game_state.game_over = False
    game_state.cheat_mode = False
    game_state.cheat_vision = False
    game_state.camera_mode = "third_person"
    game_state.frame_count = 0  # reset frame counter on restart
    
    # Spawn 5 enemies at random positions
    for _ in range(5):
        spawn_enemy()

def check_collision_sphere(pos1, pos2, radius1, radius2):
    """Check collision between two spheres using distance and radii"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
    return distance < (radius1 + radius2)

def spawn_enemy():
    """Spawn an enemy at a random position around the grid, avoiding player proximity"""
    min_distance_from_player = 100  # minimum distance from player
    
    for attempt in range(10):  # try up to 10 times to find a good position
        x = random.uniform(-GRID_LENGTH + 50, GRID_LENGTH - 50)
        z = random.uniform(-GRID_LENGTH + 50, GRID_LENGTH - 50)
        
        # Check distance from player
        dx = x - game_state.player_pos[0]
        dz = z - game_state.player_pos[2]
        distance = math.sqrt(dx*dx + dz*dz)
        
        if distance >= min_distance_from_player:
            game_state.enemies.append({
                'pos': [x, 0, z],
                'alive': True,
                'scale': 1.0
            })
            return
    
    # If no good position found, spawn at edge of grid (avoiding corners)
    edge_choices = [
        (-GRID_LENGTH + 150, random.uniform(-GRID_LENGTH + 150, GRID_LENGTH - 150)),  # left edge
        (GRID_LENGTH - 150, random.uniform(-GRID_LENGTH + 150, GRID_LENGTH - 150)),   # right edge
        (random.uniform(-GRID_LENGTH + 150, GRID_LENGTH - 150), -GRID_LENGTH + 150),  # back edge
        (random.uniform(-GRID_LENGTH + 150, GRID_LENGTH - 150), GRID_LENGTH - 150)   # front edge
    ]
    edge_x, edge_z = random.choice(edge_choices)
    game_state.enemies.append({
        'pos': [edge_x, 0, edge_z],
        'alive': True,
        'scale': 1.0
    })



def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw text on screen at specified coordinates"""
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_player():
    """Draw the player character with gun"""
    if game_state.game_over:
        # Player lies down when game is over
        glPushMatrix()
        glTranslatef(game_state.player_pos[0], 0, game_state.player_pos[2])
        glRotatef(90, 1, 0, 0)  # Rotate to lie down
        
        # Player body (sphere)
        glColor3f(0.2, 0.6, 1.0)
        gluSphere(gluNewQuadric(), 20, 10, 10)
        glPopMatrix()
        return
    
    glPushMatrix()
    glTranslatef(game_state.player_pos[0], 0, game_state.player_pos[2])
    glRotatef(game_state.player_rotation, 0, 1, 0)
    
    # Player body (sphere) - Blue color as specified
    glColor3f(0.2, 0.6, 1.0)
    gluSphere(GLOBAL_QUADRIC, 20, 10, 10)
    
    # Gun barrel (cylinder) - Dark gray metallic look
    glColor3f(0.3, 0.3, 0.3)
    glTranslatef(0, 0, 30)
    glRotatef(90, 0, 1, 0)
    gluCylinder(GLOBAL_QUADRIC, 5, 5, 40, 8, 8)
    
    # Gun handle (cuboid) - Brown wooden handle
    glColor3f(0.5, 0.3, 0.1)
    glRotatef(-90, 0, 1, 0)
    glTranslatef(0, -15, 0)
    glScalef(8, 20, 8)
    glutSolidCube(1)
    
    glPopMatrix()

def draw_enemies():
    """Draw all enemies"""
    for enemy in game_state.enemies:
        if enemy['alive']:
            glPushMatrix()
            glTranslatef(enemy['pos'][0], 0, enemy['pos'][2])
            
            # Enemy body (two spheres) - Red color as specified
            glColor3f(1.0, 0.0, 0.0)
            gluSphere(GLOBAL_QUADRIC, 15 * enemy['scale'], 10, 10)
            
            # Enemy head (smaller sphere on top)
            glTranslatef(0, 15, 0)
            gluSphere(GLOBAL_QUADRIC, 10 * enemy['scale'], 10, 10)
            
            glPopMatrix()

def draw_bullets():
    """Draw all active bullets"""
    for bullet in game_state.bullets:
        if bullet['active']:
            glPushMatrix()
            glTranslatef(bullet['pos'][0], bullet['pos'][1], bullet['pos'][2])
            
            # Bullet (cube) - Yellow color as specified
            glColor3f(1.0, 1.0, 0.0)
            glutSolidCube(8)
            
            glPopMatrix()





def draw_grid():
    """Draw the game floor as dynamic quad tiles + four vertical boundaries (no GL_LINES)."""
    tile = 50  # grid cell size

    # ---- FLOOR (X–Z plane, Y=0) ----
    for x in range(-GRID_LENGTH, GRID_LENGTH, tile):
        for z in range(-GRID_LENGTH, GRID_LENGTH, tile):
            c = ((x // tile) + (z // tile)) & 1
            if c == 0:
                glColor3f(1.0, 1.0, 1.0)      # white
            else:
                glColor3f(0.7, 0.5, 0.95)     # purple

            glBegin(GL_QUADS)
            glVertex3f(x,        0, z+tile)
            glVertex3f(x+tile,   0, z+tile)
            glVertex3f(x+tile,   0, z)
            glVertex3f(x,        0, z)
            glEnd()

    # ---- WALLS (vertical quads; Y is height) ----
    h = BOUNDARY_HEIGHT
    glColor3f(0.6, 0.6, 0.8)  # side walls

    # left wall: x = -GRID_LENGTH, spans z
    glBegin(GL_QUADS)
    glVertex3f(-GRID_LENGTH, 0, -GRID_LENGTH)
    glVertex3f(-GRID_LENGTH, 0,  GRID_LENGTH)
    glVertex3f(-GRID_LENGTH, h,  GRID_LENGTH)
    glVertex3f(-GRID_LENGTH, h, -GRID_LENGTH)
    glEnd()

    # right wall: x = +GRID_LENGTH, spans z
    glBegin(GL_QUADS)
    glVertex3f( GRID_LENGTH, 0, -GRID_LENGTH)
    glVertex3f( GRID_LENGTH, 0,  GRID_LENGTH)
    glVertex3f( GRID_LENGTH, h,  GRID_LENGTH)
    glVertex3f( GRID_LENGTH, h, -GRID_LENGTH)
    glEnd()

    glColor3f(0.8, 0.6, 0.6)  # far/near walls

    # far wall: z = +GRID_LENGTH, spans x
    glBegin(GL_QUADS)
    glVertex3f(-GRID_LENGTH, 0,  GRID_LENGTH)
    glVertex3f( GRID_LENGTH, 0,  GRID_LENGTH)
    glVertex3f( GRID_LENGTH, h,  GRID_LENGTH)
    glVertex3f(-GRID_LENGTH, h,  GRID_LENGTH)
    glEnd()

    # near wall: z = -GRID_LENGTH, spans x
    glBegin(GL_QUADS)
    glVertex3f(-GRID_LENGTH, 0, -GRID_LENGTH)
    glVertex3f( GRID_LENGTH, 0, -GRID_LENGTH)
    glVertex3f( GRID_LENGTH, h, -GRID_LENGTH)
    glVertex3f(-GRID_LENGTH, h, -GRID_LENGTH)
    glEnd()

def fire_bullet():
    """Fire a bullet from the player's gun"""
    if game_state.game_over:
        return
        
    # Calculate bullet direction based on player rotation
    angle_rad = math.radians(game_state.player_rotation)
    dx = math.sin(angle_rad)
    dz = math.cos(angle_rad)
    
    # Bullet starts at gun tip
    bullet_x = game_state.player_pos[0] + dx * 40
    bullet_z = game_state.player_pos[2] + dz * 40
    
    game_state.bullets.append({
        'pos': [bullet_x, 8, bullet_z],  # small lift to avoid z-fighting with the floor
        'spawn_pos': [bullet_x, 8, bullet_z],  # track where bullet was fired from
        'direction': [dx, 0, dz],
        'active': True
    })

def update_bullets():
    """Update bullet positions and check collisions"""
    for bullet in game_state.bullets[:]:
        if bullet['active']:
            # Move bullet
            bullet['pos'][0] += bullet['direction'][0] * BULLET_SPEED
            bullet['pos'][2] += bullet['direction'][2] * BULLET_SPEED
            
            # Check if bullet has exceeded max range OR world bounds (optimization)
            dx = bullet['pos'][0] - bullet['spawn_pos'][0]
            dz = bullet['pos'][2] - bullet['spawn_pos'][2]
            distance_traveled = math.sqrt(dx*dx + dz*dz)
            
            # Early exit if bullet is way out of bounds (optimization)
            if (abs(bullet['pos'][0]) > GRID_LENGTH + 200 or 
                abs(bullet['pos'][2]) > GRID_LENGTH + 200):
                bullet['active'] = False
                game_state.bullets_missed += 1
                if game_state.bullets_missed >= 10:
                    game_state.game_over = True
                continue
            
            # Check if bullet has exceeded max range
            if distance_traveled > BULLET_MAX_RANGE:
                bullet['active'] = False
                game_state.bullets_missed += 1
                if game_state.bullets_missed >= 10:
                    game_state.game_over = True
                continue
            
            # Check collision with enemies using improved collision detection
            for enemy in game_state.enemies:
                if enemy['alive']:
                    if check_collision_sphere(bullet['pos'], enemy['pos'], BULLET_HALF, ENEMY_RADIUS * enemy['scale']):
                        enemy['alive'] = False
                        bullet['active'] = False
                        game_state.game_score += 10
                        break

def update_enemies():
    """Update enemy positions and check player collision"""
    global game_state
    
    # Update enemy scale for shrinking/expanding effect
    game_state.enemy_scale += game_state.enemy_scale_direction
    if game_state.enemy_scale > 1.2 or game_state.enemy_scale < 0.8:
        game_state.enemy_scale_direction *= -1
    
    for enemy in game_state.enemies:
        if enemy['alive']:
            enemy['scale'] = game_state.enemy_scale
            
            # Move towards player
            dx = game_state.player_pos[0] - enemy['pos'][0]
            dz = game_state.player_pos[2] - enemy['pos'][2]
            distance = math.sqrt(dx*dx + dz*dz)
            
            if distance > 0:
                dx = dx / distance * ENEMY_SPEED
                dz = dz / distance * ENEMY_SPEED
                enemy['pos'][0] += dx
                enemy['pos'][2] += dz
            
            # Check collision with player using improved collision detection
            if check_collision_sphere(game_state.player_pos, enemy['pos'], PLAYER_RADIUS, ENEMY_RADIUS * enemy['scale']):
                if game_state.hit_cooldown == 0:  # only apply damage if not on cooldown
                    game_state.player_life -= 1
                    game_state.hit_cooldown = 45  # ~0.75s at 60fps
                    if game_state.player_life <= 0:
                        game_state.game_over = True
    




def update_cheat_mode():
    """Update cheat mode behavior"""
    if game_state.cheat_mode and not game_state.game_over:
        # Rotate gun 360 degrees
        game_state.player_rotation += 5
        
        # Check if enemy is in line of sight and fire
        for enemy in game_state.enemies:
            if enemy['alive']:
                # Calculate angle to enemy
                dx = enemy['pos'][0] - game_state.player_pos[0]
                dz = enemy['pos'][2] - game_state.player_pos[2]
                angle_to_enemy = math.degrees(math.atan2(dx, dz))
                
                # Normalize angles
                player_angle = game_state.player_rotation % 360
                angle_diff = abs(angle_to_enemy - player_angle)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                
                # Fire if enemy is roughly in front (within 15 degrees)
                if angle_diff < 15:
                    fire_bullet()
                    break

def prune_lists():
    """Remove inactive bullets and keep enemy list tidy (ensure 5 alive)."""
    # remove inactive bullets (more efficient than list comprehension for large lists)
    active_bullets = []
    for bullet in game_state.bullets:
        if bullet.get('active'):
            active_bullets.append(bullet)
    game_state.bullets = active_bullets

    # remove dead enemies completely and keep exactly 5 alive total:
    alive_enemies = []
    for enemy in game_state.enemies:
        if enemy.get('alive'):
            alive_enemies.append(enemy)
    
    # spawn new ones until we have 5 alive
    while len(alive_enemies) < 5:
        spawn_enemy()  # use the improved spawning function
        alive_enemies.append(game_state.enemies[-1])  # add the newly spawned enemy
    
    game_state.enemies = alive_enemies

def keyboardListener(key, x, y):
    """Handle keyboard input"""
    global game_state
    
    if game_state.game_over:
        if key == b'r':
            init_game()
        return
    
    if key == b'w':  # Move forward
        angle_rad = math.radians(game_state.player_rotation)
        game_state.player_pos[0] += math.sin(angle_rad) * PLAYER_SPEED
        game_state.player_pos[2] += math.cos(angle_rad) * PLAYER_SPEED
        
    elif key == b's':  # Move backward
        angle_rad = math.radians(game_state.player_rotation)
        game_state.player_pos[0] -= math.sin(angle_rad) * PLAYER_SPEED
        game_state.player_pos[2] -= math.cos(angle_rad) * PLAYER_SPEED
        
    elif key == b'a':  # Rotate left
        game_state.player_rotation -= 5
        
    elif key == b'd':  # Rotate right
        game_state.player_rotation += 5
        
    elif key == b'c':  # Toggle cheat mode
        game_state.cheat_mode = not game_state.cheat_mode
        
    elif key == b'v':  # Toggle cheat vision
        game_state.cheat_vision = not game_state.cheat_vision
    
    # Keep player within grid bounds
    game_state.player_pos[0] = max(-GRID_LENGTH + 50, min(GRID_LENGTH - 50, game_state.player_pos[0]))
    game_state.player_pos[2] = max(-GRID_LENGTH + 50, min(GRID_LENGTH - 50, game_state.player_pos[2]))
    
    glutPostRedisplay()

def specialKeyListener(key, x, y):
    """Handle special key input (arrow keys)"""
    global game_state
    
    if key == GLUT_KEY_UP:  # Move camera up
        game_state.target_camera_pos[1] += CAMERA_HEIGHT_SPEED
        
    elif key == GLUT_KEY_DOWN:  # Move camera down
        game_state.target_camera_pos[1] = max(100, game_state.target_camera_pos[1] - CAMERA_HEIGHT_SPEED)
        
    elif key == GLUT_KEY_LEFT:  # Rotate camera left
        game_state.target_camera_rotation -= CAMERA_ROTATION_SPEED
        
    elif key == GLUT_KEY_RIGHT:  # Rotate camera right
        game_state.target_camera_rotation += CAMERA_ROTATION_SPEED
    
    glutPostRedisplay()

def mouseListener(button, state, x, y):
    """Handle mouse input"""
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if not game_state.game_over:
            fire_bullet()
            
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        if game_state.camera_mode == "third_person":
            game_state.camera_mode = "first_person"
        else:
            game_state.camera_mode = "third_person"
    
    glutPostRedisplay()

def setupCamera():
    """Setup camera perspective and position"""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(120, 1.25, 0.1, 1500)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if game_state.camera_mode == "first_person":
        angle_rad = math.radians(game_state.player_rotation)

        # base eye looking forward from player
        fwd_x = math.sin(angle_rad)
        fwd_z = math.cos(angle_rad)

        # default first-person eye
        eye_x = game_state.player_pos[0] + fwd_x * 30
        eye_z = game_state.player_pos[2] + fwd_z * 30
        eye_y = 20

        # if cheat vision => tweak eye to follow gun motion "visibly"
        if game_state.cheat_vision:
            eye_y = 30                      # a bit higher
            eye_x -= fwd_x * 10             # slight pull-back to see barrel spin
            eye_z -= fwd_z * 10

        look_x = game_state.player_pos[0] + fwd_x * 100
        look_z = game_state.player_pos[2] + fwd_z * 100

        gluLookAt(eye_x, eye_y, eye_z,
                  look_x, 10, look_z,  # look slightly above ground for better view
                  0, 1, 0)
    else:
        angle_rad = math.radians(game_state.camera_rotation)
        cam_x = game_state.player_pos[0] + math.sin(angle_rad) * 500
        cam_z = game_state.player_pos[2] + math.cos(angle_rad) * 500
        cam_y = game_state.camera_pos[1]
        
        # if cheat vision => adjust third-person camera for better visibility
        if game_state.cheat_vision:
            cam_y += 50  # higher camera position
            # look slightly ahead of player for better targeting
            look_x = game_state.player_pos[0] + math.sin(angle_rad) * 50
            look_z = game_state.player_pos[2] + math.cos(angle_rad) * 50
        else:
            look_x = game_state.player_pos[0]
            look_z = game_state.player_pos[2]

        gluLookAt(cam_x, cam_y, cam_z,
                  look_x, 0, look_z,
                  0, 1, 0)

def showScreen():
    """Main display function"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    
    setupCamera()
    
    # Draw game elements
    draw_grid()
    draw_player()
    draw_enemies()
    draw_bullets()
    
    # Draw UI text
    draw_text(10, 770, f"Life: {game_state.player_life}")
    draw_text(10, 740, f"Score: {game_state.game_score}")
    draw_text(10, 710, f"Bullets Missed: {game_state.bullets_missed}")
    draw_text(10, 680, f"Enemies: {len([e for e in game_state.enemies if e.get('alive')])}")
    draw_text(10, 650, f"Bullets: {len([b for b in game_state.bullets if b.get('active')])}")
    draw_text(10, 620, f"Frame: {game_state.frame_count}")
    
    if game_state.cheat_mode:
        draw_text(10, 590, "CHEAT MODE: ON")
    if game_state.cheat_vision:
        draw_text(10, 560, "CHEAT VISION: ON")
    if game_state.camera_mode == "first_person":
        draw_text(10, 530, "Camera: First Person")
    else:
        draw_text(10, 530, "Camera: Third Person")
    
    if game_state.game_over:
        draw_text(400, 400, "GAME OVER!")
        draw_text(400, 370, "Press R to Restart")
    
    glutSwapBuffers()

def idle():
    """Idle function for continuous updates"""
    if not game_state.game_over:
        game_state.frame_count += 1  # performance monitoring
        
        if game_state.hit_cooldown > 0:
            game_state.hit_cooldown -= 1
        
        # Smooth camera rotation interpolation
        if abs(game_state.camera_rotation - game_state.target_camera_rotation) > 0.1:
            diff = game_state.target_camera_rotation - game_state.camera_rotation
            game_state.camera_rotation += diff * game_state.camera_smooth_factor
        
        # Smooth camera position interpolation (height and distance)
        for i in range(3):
            if abs(game_state.camera_pos[i] - game_state.target_camera_pos[i]) > 0.1:
                diff = game_state.target_camera_pos[i] - game_state.camera_pos[i]
                game_state.camera_pos[i] += diff * game_state.camera_smooth_factor
        
        update_bullets()
        update_enemies()
        update_cheat_mode()
        prune_lists()      # prune each frame (cheap)
    
    glutPostRedisplay()

def main():
    """Main function to initialize and run the game"""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    wind = glutCreateWindow(b"Bullet Frenzy - 3D Game")
    
    # Initialize game
    init_game()
    
    # Register callbacks
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    
    # Enable performance optimizations
    prepare_batch_rendering()
    
    glutMainLoop()

if __name__ == "__main__":
    main()
