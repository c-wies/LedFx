import logging
import os
import Enum

import voluptuous as vol

from ledfx.effects import Effect
from ledfx.effects.twod import Twod
from ledfx.consts import LEDFX_ASSETS_PATH
from ledfx.color import parse_color, validate_color

from PIL import Image, ImageDraw, ImageFont

_LOGGER = logging.getLogger(__name__)

DEBUG = False

FONT_MAPPINGS = {
    "Roboto Regular": os.path.join(LEDFX_ASSETS_PATH, "fonts", "Roboto-Regular.ttf"),
    "Roboto Bold": os.path.join(LEDFX_ASSETS_PATH, "fonts", "Roboto-Bold.ttf"),
    "Roboto Black": os.path.join(LEDFX_ASSETS_PATH, "fonts", "Roboto-Black.ttf"),
    "Stop": os.path.join(LEDFX_ASSETS_PATH, "fonts", "Stop.ttf"),
    "04b_30": os.path.join(LEDFX_ASSETS_PATH, "fonts", "04b_30__.ttf"),
    "8bitOperatorPlus8": os.path.join(LEDFX_ASSETS_PATH, "fonts", "8bitOperatorPlus8-Regular.ttf")}

class Mode(Enum):
    HOLD = 1
    BOUNCE = 2
    HARD_ZERO = 3
    DECELERATE = 4

class Scalar():
    def __init__(self, val, delta, target, target_2, mode):
        self.val = val
        self.delta = delta
        self.target = target
        self.target_2 = target_2
        self.mode = mode

    def update(self, passed_time):
        self.val += self.delta * passed_time
        if self.delta > 0:
            self.val = min(self.val, self.target)
        else:
            self.val = max(self.val, self.target)
        if self.val == self.target:
            if self.mode == Mode.HOLD:
                self.delta = 0
            elif self.mode == Mode.BOUNCE:
                self.delta = -self.delta
                self.target, self.target_2 = self.target_2, self.target
            elif self.mode == Mode.HARD_ZERO:
                self.delta = 0
                self.val = 0
            elif self.mode == Mode.DECELERATE:
                self.delta = self.delta * 0.5


class Textblock():
    # this class is intended to establish a pillow image object with rendered text within it
    # text will be created from the passed font at the requested size
    # the pillow image will have an alpha channel, and will always be transparent
    # the text will be rendered in the color requested
    # the text will be centered in the image which is only big enough to contain the text
    # the Textblock instance will be merged into the main display image outside of this class
    # so TextBlock has no idea of position which will be handled externally to this class

    def __init__(self, text, font, color='white'):
        self.text = text
        # open the font file
        self.color = color
        self.ascent, self.descent = font.getmetrics()
        dummy_image = Image.new('RGB', (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_image)
        left, top, right, bottom = dummy_draw.textbbox((0,0), text, font=font)
        self.width = right - left
        self.height = self.descent + self.ascent
        self.image = Image.new('RGBA', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self.draw.text((0, 0), self.text, font=font, fill=color)
        # self.image.show()

    def set_pos_life(self, x, y,
                     vector_linear, vector_linear_delta, vector_linear_target,
                     vector_angular, vector_angular_delta, vectro_angular_target,
                     rotation, rotation_delta, rotation_target,
                     size, size_delta, size_target,
                     life):
        # pos is -1 to 1 for (x, y) tuple
        self.x = x
        self.y = y
        self.vector_linear = Scalar()
        self.vector_angular = Scalar()
        self.rotation = Scalar()
        self.size = Scalar()
        self.life = life

    def update(self, passed_time):
        self.life = max(self.life - passed_time, 0.0)
        if self.life > 0.0:
            self.vector_linear.update(passed_time)
            self.vector_angular.update(passed_time)
            # calculate new x and y using vector_linear and vector_angular
            # self.vector_linear is a scalar for x and y in the range -1 to 1
            # it must be applied along with self.vector_angular to get the new x and y

            # I need to use a vector class to do this
            # self.x,

            self.x =


            self.rotation.update(passed_time)
            self.size.update(passed_time)

    def render(self, target):
        # first we will rotate and then size the image
        # ang is a rotation from 0 to 1 float to represent 0 to 360 degrees
        # size is a float from 0 to 1 to represent 0 to 100% size
        resized = self.image.rotate(self.rotation.val * 360, expand=True)
        resized = resized.resize((int(resized.width * self.size.val), int(resized.height * self.size.val)))
        # self.pos is a scalar for x and y in the range -1 to 1
        # the pos position is for the center of the image
        # here we will convert it to a pixel position within target which is a PIL image object
        pos_xy = (int((self.x + 1) * target.width / 2 - resized.width / 2),
                  int((self.y + 1) * target.height / 2 - resized.height / 2))

        target.paste(resized, pos_xy, resized)


class Sentence():
    # this class will construct and maintain a set of words,
    # spaces and animated dynamics for a sentence

    ANIMATIONS = {
        "SIDE_SCROLL"
    }

    def __init__(self, text, font_name, points, start_color='white'):
        self.text = text
        self.font_path = FONT_MAPPINGS[font_name]
        self.points = points
        self.start_color = parse_color(start_color)
        self.font = ImageFont.truetype(self.font_path, self.points)
        self.wordblocks = []

        for word in self.text.split():
            wordblock = Textblock(word,
                             self.font,
                             self.start_color)
            self.wordblocks.append(wordblock)
            _LOGGER.info(f"Wordblock {word} created")
            if DEBUG:
                wordblock.image.show()
        space_block = Textblock(" ",
                                self.font)
        self.space_width = space_block.width
        _LOGGER.info(f"Space width is {self.space_width}")


        for idx, word in enumerate(self.wordblocks):
            word.set_pos_life((-1 + idx * 0.2, -1 + idx * 0.2), (0, 0), 0.1 * idx, 0.2, 1)
            _LOGGER.info(f"{idx} {word.text} {word.width} {word.height} {word.pos} {word.vel} {word.ang} {word.size} {word.life}")

    def update(self, passed_time):
        for word in self.wordblocks:
            word.update(passed_time)

    def render(self, target):
        for word in self.wordblocks:
            if word.life > 0:
                word.render(target)

class Texter2d(Twod):
    NAME = "Texter"
    CATEGORY = "Matrix"
    # add keys you want hidden or in advanced here
    HIDDEN_KEYS = Twod.HIDDEN_KEYS + []
    ADVANCED_KEYS = Twod.ADVANCED_KEYS + []

    CONFIG_SCHEMA = vol.Schema(
        {
            vol.Optional(
                "a_switch",
                description="Does a boolean thing",
                default=False,
            ): bool,
            vol.Optional(
                "font",
                description="Font to render text with",
                default="8bitOperatorPlus8",
            ): vol.In(list(FONT_MAPPINGS.keys())),
            vol.Optional(
                "text",
                description="Your text to display",
                default="Your text here",
            ): str,
            vol.Optional(
                "height_percent",
                description="Font size as a percentage of the display height",
                default=75,
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=150)),
            vol.Optional(
                "text_color",
                description="Color of text",
                default="#FFFFFF",
            ): validate_color,
        },
    )

    def __init__(self, ledfx, config):
        super().__init__(ledfx, config)
        self.bar = 0

    def config_updated(self, config):
        super().config_updated(config)
        # copy over your configs here into variables
        self.a_switch = self._config["a_switch"]

    def do_once(self):
        super().do_once()
        # self.r_width and self.r_height should be used for the (r)ender space
        # as the self.matrix will not exist yet
        self.sentence = Sentence(self.config["text"],
                                 self.config["font"],
                                 int(self.r_height * self.config["height_percent"] / 100),
                                 self.config["text_color"])

    def audio_data_updated(self, data):
        # Grab your audio input here, such as bar oscillator
        self.bar = data.bar_oscillator()

    def draw(self):
        # self.matrix is the Image object
        # self.m_draw is the attached draw object

        # self.matrix.height
        # self.matrix.width

        if self.test:
            self.draw_test(self.m_draw)

        self.sentence.render(self.matrix)
        # stuff pixels with
        # self.matrix.putpixel((x, y), (r, g, b))
        # or
        # pixels = self.matrix.load()
        # pixels[x, y] = (r, g, b)
        #   iterate
