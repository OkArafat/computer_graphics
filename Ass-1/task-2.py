import sys  
import random 
import time  
from OpenGL.GL import *  
from OpenGL.GLUT import *  
from OpenGL.GLU import *  

points = []  
freeze = False 
blinking_active = False  
blink_phase = 0  
last_blink_toggle_time = 0 
window_width, window_height = 1000, 1000 
point_size = 5.0 

def init():  # Initial setup function
    glClearColor(0.0, 0.0, 0.0, 1.0)  
    gluOrtho2D(-100, 100, -100, 100)  

def draw_box():  
    glColor3f(1.0, 1.0, 1.0)  
    glBegin(GL_LINE_LOOP) 
    glVertex2f(-100, -100)  
    glVertex2f(100, -100) 
    glVertex2f(100, 100)  
    glVertex2f(-100, 100)  
    glEnd()  

def draw_points():  
    glPointSize(point_size) 
    glBegin(GL_POINTS) 
    for point in points:
        x, y, color, dx, dy, speed = point  # Point er value gulo ber kora
        if blinking_active and blink_phase == 1:  # Jodi blink cholche o phase 1 hoy
            glColor3f(0.0, 0.0, 0.0)  
        else:
            r, g, b = color  # Color value gulo ber kora
            glColor3f(r, g, b)  
        glVertex2f(x, y)  # Point er position set kora hocche
    glEnd()  # Point drawing sesh

def display():  # Display function
    glClear(GL_COLOR_BUFFER_BIT)  
    draw_box()  
    draw_points()  
    glutSwapBuffers()  

def update_points():  # Point update korar function
    global points, freeze, blinking_active, blink_phase, last_blink_toggle_time  # Global variable gulo use korbo
    current_time = time.time()  
    
 
    if blinking_active and current_time - last_blink_toggle_time >= 0.5:  
        blink_phase = 1 - blink_phase  
        last_blink_toggle_time = current_time  
        glutPostRedisplay() 
    if not freeze:  # Freeze na thakle
        for point in points: 
            x, y, color, dx, dy, speed = point  # Value gulo ber kora
            new_x = x + dx * speed  
            new_y = y + dy * speed  
            
      
            if new_x > 100 or new_x < -100:  
                dx = -dx 
                new_x = x + dx * speed  
            if new_y > 100 or new_y < -100:  # Y boundary cross korle
                dy = -dy  # Y direction ulta koro
                new_y = y + dy * speed  
            
            # Update point position and direction  # Point er value update koro
            point[0] = new_x  
            point[1] = new_y 
            point[3] = dx  
            point[4] = dy  
        
        glutPostRedisplay()  # Display abar draw koro

def mouse(button, state, x, y):  
    global points, freeze, blinking_active, blink_phase, last_blink_toggle_time  # Global variable gulo use korbo
    
    if freeze: 
        return  
    
    win_x = (x / window_width) * 200 - 100  
    win_y = 100 - (y / window_height) * 200  #
    
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN: 
       
        color = (random.random(), random.random(), random.random())  
        dx, dy = random.uniform(-1, 1), random.uniform(-1, 1) 
        speed = 1.0  
        points.append([win_x, win_y, color, dx, dy, speed])  # Point add kora
        glutPostRedisplay()  
    
    elif button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:  # Left click dile
        # Toggle blinking mode  # Blinking on/off koro
        blinking_active = not blinking_active  # Blinking toggle
        if blinking_active: 
            blink_phase = 0  
            last_blink_toggle_time = time.time()  # Last blink time set koro
        glutPostRedisplay()  

def keyboard(key, x, y):  
    global freeze, points 
    
    if key == b' ': 
        freeze = not freeze 
    glutPostRedisplay()  

def special_keys(key, x, y):  
    global freeze, points  
    if freeze: 
        return 
    
    if key == GLUT_KEY_UP:  # Up arrow
        for point in points:  # Prottek point er jonno
            point[5] *= 1.1  # Speed barai
    elif key == GLUT_KEY_DOWN:  # Down arrow
        for point in points:  
            point[5] *= 0.9  
    glutPostRedisplay()  

def main():  # Main function
    glutInit(sys.argv)  # GLUT initialize kora hocche
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)  
    glutInitWindowSize(window_width, window_height)  
    glutCreateWindow(b"Amazing Box")  
    init() 
    glutDisplayFunc(display) 

    glutIdleFunc(update_points) 
    
    glutMouseFunc(mouse)  
    glutKeyboardFunc(keyboard) 
    glutSpecialFunc(special_keys) 
    glutMainLoop()  

if __name__ == "__main__":  
    main() 