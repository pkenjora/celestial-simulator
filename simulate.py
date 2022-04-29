#!/usr/bin/python3

import argparse
import textwrap
import pygame 
import math 

from importlib import import_module
from pygame.colordict import THECOLORS

# Inspired By: https://github.com/enosjeba/Planet-Simulation

pygame.init()
WIN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = WIN.get_size()
FONT = pygame.font.SysFont("comicsans", 16)


class Body:
  ''' Define a generic celestial object to help with positioning and rendering.'''

  PLANET_SCALE = 3000

  def __init__(self, name, x, y, x_vel, y_vel, mass, diameter, color, parent=None):
    ''' A fixed coordinate system for starting positions allows the most flexibility.

        Args:
          name (string) - just a label
          x,y (float, float) - the coordinates to start at, 0,0 being the center
          x_vel, y_vel (float, float) - the velocity vectors at start time
          mass (float) - kilograms, very important affects gravity
          diameter (float) - meters, should be actual object size, not rendered to scale
          color (string) - the color name as understtod by pygame
          parent (Body) - the celestial body this object is supposed to orbit ( for reference )
    '''

    self.name = name
    self.x = x 
    self.y = y 
    self.diameter = diameter 
    self.color = color
    self.mass = mass
      
    self.orbit = []
    self.parent = parent
    self.distance_to_parent = 0
      
    self.x_vel = x_vel
    self.y_vel = y_vel
      
    self.x_force = 0
    self.y_force = 0


  def draw(self, win, scale):
    ''' Render the object with historic path adjusting for screen scale.

        Args:
          win (pygame) - the pygame window object to render into.
          scale - the scaling factor to fit the render on the screen, depends on initial objects.
    '''
    self.orbit.append((self.x, self.y))

    x = self.x * scale + WIDTH / 2
    y = self.y * scale + HEIGHT / 2

    if len(self.orbit) > 2:
      updated_points = []
      for point in self.orbit:
        x, y = point
        x = x * scale + WIDTH / 2
        y = y * scale + HEIGHT / 2
        updated_points.append((x,y))

      pygame.draw.lines(win, THECOLORS[self.color], False, updated_points, 1)
     
    pygame.draw.circle(win,self.color,(x,y), max(1, min(self.diameter / Body.PLANET_SCALE, 20)))

    #if self.parent:
    #  distance_text = FONT.render(f"{self.name}: {round(self.distance_to_parent/1000, 0)}km", 1, THECOLORS['white'])
    #  win.blit(distance_text, (x - distance_text.get_width()/4, y - distance_text.get_width()/4))
      

class Star(Body):
  ''' An object not inherently orbiting any others.'''

  def __init__(self, name, x, y, angle, velocity, mass, diameter, color):
    ''' Helper translates angular velocity to vectors in coordinate space.

        Args:
          name (string) - just a label
          x,y (float, float) - the coordinates to start at, 0,0 being the center
          angle (float) - Direction of motion around 0, 0 coordinate in degrees 
          velocity (float) - Velocity in meters per second
          mass (float) - kilograms, very important affects gravity
          diameter (float) - meters, should be actual object size, not rendered to scale
          color (string) - the color name as understtod by pygame
    '''

    angle_v = math.radians(angle)
    x_vel = math.cos(angle_v) * velocity
    y_vel = math.sin(angle_v) * velocity 

    super().__init__(name, x, y, x_vel, y_vel, mass, diameter, color)


class Planet(Body):

  def __init__(self, star, name, angle, distance, velocity, mass, diameter, color):
    ''' Helper translates position and velocity around parent body in coordinate space.

        Args:
          name (Body) - parent object
          name (string) - just a label
          angle (float) - Position in degrees around parent object
          distance (float) - Distance from parent in meters
          velocity (float) - Velocity in meters per second, assumed to be 90 degrees to position
          mass (float) - kilograms, very important affects gravity
          diameter (float) - meters, should be actual object size, not rendered to scale
          color (string) - the color name as understtod by pygame
    '''

    angle_d = math.radians(angle)
    x = star.x + math.cos(angle_d) * distance
    y = star.y + math.sin(angle_d) * distance

    angle_v = math.radians(angle + 90)
    x_vel = star.x_vel + math.cos(angle_v) * velocity
    y_vel = star.y_vel + math.sin(angle_v) * velocity 

    super().__init__(name, x, y, x_vel, y_vel, mass, diameter, color, star)

class Moon(Planet): 
  ''' Identical properties as a planet except parent is a planet instead of a star.'''

  def __init__(self, planet, name, angle, distance, velocity, mass, diameter, color):
    super().__init__(planet, name, angle, distance, velocity, mass, diameter, color)


class Simulation():
  ''' Contains all celestial objects, calculates positions, and triggers renders. '''

  G = 6.67428e-11 # Gravitational constant used for all position calculations
  TIMESPAN = 60 # Number of seconds between calculations ~ 1 minute - IF THIS IS TOO LARGE THE SIMULATION BREAKS
  TIMESTEP = 60 * 24 # Number of calculations between renders ~ 1 day

  def __init__(self, system_file):
    ''' Load a celestial definition file and calculate scale for rendering.
        Args:
          system_file (string) - Name of python module containing the celestial defintions
    '''

    self.bodies = []
    system = getattr(import_module(system_file), 'SYSTEM')
    for star in system:
      s = Star(
        name=star['name'],
        x=star['x'],
        y=star['y'],
        angle=star['angle'],
        velocity=star['velocity'],
        mass=star['mass'],
        diameter=star['diameter'],
        color=star['color']
      )
      self.bodies.append(s)
      for planet in star.get('planets', []):
        p = Planet(
          star=s,
          name=planet['name'],
          angle=planet['angle'],
          distance=planet['distance'],
          velocity=planet['velocity'],
          mass=planet['mass'],
          diameter=planet['diameter'],
          color=planet['color']
        )
        self.bodies.append(p)
        for moon in planet.get('moons', []):
          m = Moon(
            planet=p,
            name=moon['name'],
            angle=moon['angle'],
            distance=moon['distance'],
            velocity=moon['velocity'],
            mass=moon['mass'],
            diameter=moon['diameter'],
            color=moon['color']
          )
          self.bodies.append(m)

    self.scale = min(WIDTH, HEIGHT) / (max(math.sqrt(p.x**2 + p.y**2) for p in self.bodies)) / 2.1


  @staticmethod
  def attraction(first, second):
    ''' Calculate the gravitational force effects between two objects in the system.
 
        Args:
          first (Body) - a celestial body object 
          second (Body) - a celestial body object 
    '''

    distance_x = second.x - first.x
    distance_y = second.y - first.y
    distance = math.sqrt(distance_x ** 2 + distance_y ** 2)

    if first.parent == second:
      first.distance_to_parent = distance

    if second.parent == first:
      second.distance_to_parent = distance

    force = Simulation.G * first.mass * second.mass / distance ** 2

    theta = math.atan2(distance_y, distance_x)
    x_force = math.cos(theta) * force
    y_force = math.sin(theta) * force

    first.x_force += x_force
    first.y_force += y_force
    second.x_force -= x_force
    second.y_force -= y_force


  def update_positions(self):
    ''' Perform mathematical loops that increment positions of all objects.'''

    for iteration in range(0, Simulation.TIMESTEP): 

      # clear forces since last draw, render once per calculation cycle
      for body in self.bodies:
        body.x_force = 0
        body.y_force = 0
        if iteration == 0:
          body.draw(WIN, self.scale)

      for first_index in range(0, len(self.bodies)):

        # calculate all forces first to get a static snapshot of the system
        for second_index in range(first_index + 1, len(self.bodies)):
          Simulation.attraction(self.bodies[first_index], self.bodies[second_index])

        #calculate velocity
        self.bodies[first_index].x_vel += self.bodies[first_index].x_force / self.bodies[first_index].mass * Simulation.TIMESPAN
        self.bodies[first_index].y_vel += self.bodies[first_index].y_force / self.bodies[first_index].mass * Simulation.TIMESPAN

        # calculate position
        self.bodies[first_index].x += self.bodies[first_index].x_vel * Simulation.TIMESPAN
        self.bodies[first_index].y += self.bodies[first_index].y_vel * Simulation.TIMESPAN

    # draw planet positions as table
    self.draw()


  def draw(self):
    ''' Render the textual table in the upper right hand corner with each celestial body. '''

    y = 0
    for body in self.bodies:
      if body.parent:
        y += 20
        distance_text = FONT.render(f"{body.name}: {int(body.distance_to_parent/1000)}km", 1, THECOLORS[body.color])
        WIN.blit(distance_text, (10, y))


  def run(self):
    ''' Execute the simulation. Check for ESC or click on X to shutdown. '''

    running = True #to start the loop to keep it running
    clock = pygame.time.Clock() #to keep running the simulation on specified time

    while running: 
      clock.tick(60) #Changes will occur at 60 tick rate
      WIN.fill((0,0,0)) #Window Bg
                
      for event in pygame.event.get(): 
        if event.type == pygame.QUIT: #To quit on clicking the X
          running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
          running = False
                
      self.update_positions()

      pygame.display.update() #To update the display with newly added codes

    pygame.quit()
            
        
if __name__ == "__main__":

  parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent("Run a celestial body simulator using nothing but a universal constant!"))

  parser.add_argument('-load', help='Name of the python module holding the system defintion.', default='solar')

  args = parser.parse_args()

  Simulation(args.load.replace('.py', '')).run()
