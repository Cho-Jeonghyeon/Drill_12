from pico2d import *
import common
import random
import math
import game_framework
import game_world
from behavior_tree import BehaviorTree, Action, Sequence, Condition, Selector


PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)


TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10.0

animation_names = ['Walk', 'Idle']


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images == None:
            Zombie.images = {}
            for name in animation_names:
                Zombie.images[name] = [load_image("./zombie/" + name + " (%d)" % i + ".png") for i in range(1, 11)]
            Zombie.font = load_font('ENCR10B.TTF', 40)
            Zombie.marker_image = load_image('hand_arrow.png')

    def __init__(self, x=None, y=None):
        self.bt = None
        self.x = x if x else random.randint(100, 1180)
        self.y = y if y else random.randint(100, 924)
        self.load_images()
        self.dir = 0.0
        self.speed = 0.0
        self.frame = random.randint(0, 9)
        self.state = 'Idle'
        self.ball_count = 0
        self.tx, self.ty = 0, 0

        #BT
        self.build_behavior_tree()

    def get_bb(self):
        return self.x - 50, self.y - 50, self.x + 50, self.y + 50

    def update(self):
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * game_framework.frame_time) % FRAMES_PER_ACTION
        self.bt.run()

    def draw(self):
        if math.cos(self.dir) < 0:
            Zombie.images[self.state][int(self.frame)].composite_draw(0, 'h', self.x, self.y, 100, 100)
        else:
            Zombie.images[self.state][int(self.frame)].draw(self.x, self.y, 100, 100)

        Zombie.font.draw(self.x - 10, self.y + 60, f'{self.ball_count}', (0, 0, 255))
        Zombie.marker_image.draw(self.tx+25, self.ty-25)
        draw_rectangle(*self.get_bb())

    def handle_collision(self, group, other):
        if group == 'zombie:ball':
            self.ball_count += 1



    # 거리 체크 함수 (기존 코드 그대로)
    def distance_less_than(self, x1, y1, x2, y2, r):
        distance2 = (x1 - x2) ** 2 + (y1 - y2) ** 2
        return distance2 < (PIXEL_PER_METER * r) ** 2



    #이동 함수
    def move_little_to(self, tx, ty):
        self.dir = math.atan2(ty - self.y, tx - self.x)
        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)



    #소년에게 추적
    def move_to_boy(self):
        self.state = 'Walk'
        self.move_little_to(common.boy.x, common.boy.y)
        return BehaviorTree.RUNNING


    #소년에게서 도망
    def runaway_from_boy(self):
        self.state = 'Walk'
        boy = common.boy
        dx = self.x - boy.x
        dy = self.y - boy.y
        ang = math.atan2(dy, dx)  # 반대 방향

        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += distance * math.cos(ang)
        self.y += distance * math.sin(ang)
        return BehaviorTree.RUNNING



    #배회
    def wander(self):
        self.state = 'Walk'
        self.dir += (random.random() - 0.5) * 0.2
        distance = RUN_SPEED_PPS * game_framework.frame_time * 0.5
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)
        return BehaviorTree.RUNNING



    def build_behavior_tree(self):

        #7m 범위 체크
        c_boy_in_range = Condition('소년이 7m 안?',
            lambda: BehaviorTree.SUCCESS
            if self.distance_less_than(self.x, self.y, common.boy.x, common.boy.y, 7)
            else BehaviorTree.FAIL
        )

        #공 개수 비교
        c_more_balls = Condition('좀비 공 >= 소년 공?',
            lambda: BehaviorTree.SUCCESS
            if self.ball_count >= common.boy.ball_count
            else BehaviorTree.FAIL
        )

        c_less_balls = Condition('좀비 공 < 소년 공?',
            lambda: BehaviorTree.SUCCESS
            if self.ball_count < common.boy.ball_count
            else BehaviorTree.FAIL
        )


        a_chase = Action('소년 추적', self.move_to_boy)
        a_runaway = Action('소년 도망', self.runaway_from_boy)
        a_wander = Action('배회', self.wander)

        chase_seq = Sequence('추적 시퀀스', c_boy_in_range, c_more_balls, a_chase)
        flee_seq = Sequence('도망 시퀀스', c_boy_in_range, c_less_balls, a_runaway)

        # 최상위 Selector
        root = Selector('최종 행동 선택', chase_seq, flee_seq, a_wander)

        self.bt = BehaviorTree(root)
