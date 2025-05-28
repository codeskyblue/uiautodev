# Ref
# https://github.com/Genymobile/scrcpy/blob/master/app/src/android/input.h
from enum import IntEnum


class MetaState(IntEnum):
    """Android meta state flags ported from Android's KeyEvent class
    
    These flags represent the state of meta keys such as ALT, SHIFT, CTRL, etc.
    They can be combined using bitwise OR operations to represent multiple
    meta keys being pressed simultaneously.
    
    The values and comments are taken directly from the Android source code
    to maintain compatibility and provide accurate descriptions.
    """
    # No meta keys are pressed
    NONE = 0x0
    
    # This mask is used to check whether one of the SHIFT meta keys is pressed
    SHIFT_ON = 0x1
    
    # This mask is used to check whether one of the ALT meta keys is pressed
    ALT_ON = 0x2
    
    # This mask is used to check whether the SYM meta key is pressed
    SYM_ON = 0x4
    
    # This mask is used to check whether the FUNCTION meta key is pressed
    FUNCTION_ON = 0x8
    
    # This mask is used to check whether the left ALT meta key is pressed
    ALT_LEFT_ON = 0x10
    
    # This mask is used to check whether the right ALT meta key is pressed
    ALT_RIGHT_ON = 0x20
    
    # This mask is used to check whether the left SHIFT meta key is pressed
    SHIFT_LEFT_ON = 0x40
    
    # This mask is used to check whether the right SHIFT meta key is pressed
    SHIFT_RIGHT_ON = 0x80
    
    # This mask is used to check whether the CAPS LOCK meta key is on
    CAPS_LOCK_ON = 0x100000
    
    # This mask is used to check whether the NUM LOCK meta key is on
    NUM_LOCK_ON = 0x200000
    
    # This mask is used to check whether the SCROLL LOCK meta key is on
    SCROLL_LOCK_ON = 0x400000
    
    # This mask is used to check whether one of the CTRL meta keys is pressed
    CTRL_ON = 0x1000
    
    # This mask is used to check whether the left CTRL meta key is pressed
    CTRL_LEFT_ON = 0x2000
    
    # This mask is used to check whether the right CTRL meta key is pressed
    CTRL_RIGHT_ON = 0x4000
    
    # This mask is used to check whether one of the META meta keys is pressed
    META_ON = 0x10000
    
    # This mask is used to check whether the left META meta key is pressed
    META_LEFT_ON = 0x20000
    
    # This mask is used to check whether the right META meta key is pressed
    META_RIGHT_ON = 0x40000


class KeyeventAction(IntEnum):
    DOWN = 0
    UP = 1
    MULTIPLE = 2
