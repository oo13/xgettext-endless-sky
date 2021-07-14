#!/usr/bin/python3
# -*- coding: utf-8-unix -*-
"""A parser of Endless Sky data files for gettext."""
#
# Copyright © 2018, 2021 OOTA, Masato
#
# This is published by CC0 1.0.
# For more information, see CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
# at https://creativecommons.org/publicdomain/zero/1.0/deed).
#
# Some messages have a message context:
# Attribute labels of outfits and ships: "Label of Attribute"
# Attribute of outfits and ships: "Attribute"
# NPC ship names: "ship"
# Special log keys: "log"
# Category items: "category"
# Commodity names and items: "commodity"
# Conversations at the top level: "conversation: " + name
# Conversations in any missions: "mission: " + name
# Fullname formats in languages: "preferences"
# Galaxy sprites: "galaxy"
# Government names: "government"
# Interface buttons, labels, and strings: "interface"
# All licenses in the player info panel: "license: "
# Minable names: "minable"
# Mission cargos: "cargo"
# Mission names: "mission"
# Outfit names and their plural forms: "outfit"
# Person ship names: "person"
# Planet names: "planet"
# Rating titles: "rating"
# All salaries in the player info panel: "salary: "
# Ship's model names, their plural forms, names, and nouns: "ship"
# Start names: "start"
# System names: "system"
# Sort keys for outfit names, ship's model names, and special log names: "sort key"
# otherwise : no context

# The class enum.Enum is too slow!
( _ST_INDENT, _ST_SEARCH_TOKEN, _ST_TOKEN ) = range(3)

def _split_words(line):
    """Split into words from a line and check the size of indent.

The argument 'line' must not have '\n' except line[-1].
If line[-1] is '\n', delimiters[-1][-1] in the return value shall be '\n'.

The return value is a tuple of:
[0]: The list of words.
[1]: The list of quotations.
[2]: The list of delimiters.
[3]: The size of indent.

The size of quotations is equal to the size of words.
The size of delimiters is one more than the size of words.

quotations[n] is the quoting character of the words[n]. If words[n] has no quote, quotations[n] is empty.
delimiters[n] is the string as the delimiter before words[n] and delimiters[n+1] is after words[n].
delimters[0] includes the indent of the line.
"""
    if len(line) == 0:
        return ([], [], [], 0)
    st = _ST_INDENT
    words = []
    quotations = []
    delims = [ '' ]
    indent_number = 0
    for idx in range(len(line)):
        c = line[idx]
        if st == _ST_INDENT:
            if c == '\n':
                delims[-1] += c
                break
            elif ord(c) <= ord(' '):
                delims[-1] += c
                indent_number += 1
                continue
            else:
                st = _ST_SEARCH_TOKEN # fall through
        if st == _ST_SEARCH_TOKEN:
            if ord(c) <= ord(' '):
                delims[-1] += c
            elif c == '#':
                delims[-1] += line[idx:]
                break
            else:
                delims.append('')
                st = _ST_TOKEN
                if c == '"' or c == '`':
                    quotations.append(c)
                    words.append('')
                else:
                    quotations.append('')
                    words.append(c)
        elif st == _ST_TOKEN:
            if quotations[-1] != '' and quotations[-1] == c:
                st = _ST_SEARCH_TOKEN
            elif quotations[-1] == '' and ord(c) <= ord(' '):
                delims[-1] += c
                st = _ST_SEARCH_TOKEN
            else:
                words[-1] += c
    if delims[-1] == '':
        delims = delims[0:-1]
    return (words, quotations, delims, indent_number)


# GLOSSARY
# target line is focused by the parser at the point.
#
#    parent line
#         words[0] words[1] ... words[n]  <- target line
#             child line#1
#             ...
#             child line#n
#         next line
#
# block is a set of lines from the target line to the last line of the children (child line#n).
# here text is a special block in which a msgid is the whole string except the indent.
#
# msgid is a word that shall be translated.
# msgid context/comment is the msgctxt/comment string that corresponds to a msgid. Generally, msgid context/comment is generated by the current context/comment and the words in the target line.
#
# child context/comment is a string used to generate the msgid context/comment in a child line.
#
# (current) context/comment is the child context/comment of the parent line.

class _ParseItem:
    """An item of the parse table representing a block."""
    def __init__(self, keyword, pos = (), msgid_context_fmt = '', msgid_comment_fmt = ''):
        """If keyword is equal to words[0], this instance will be used to parse the line.
pos is the indices of all msgids. The type of pos is int or tuple of int. In a pos, same number must not appear multiple times.
msgid_context_fmt is to generate the msgid context for all msgids. The msgid context will be generated by msgid_context_fmt.format(context, *words).
msgid_comment_fmt is a variant of the msgid_context_fmt for comment.
"""
        self.keyword = keyword
        if type(pos) is int:
            self.pos = (pos, )
        else:
            self.pos = pos
        self.msgid_context_fmt = msgid_context_fmt
        self.msgid_comment_fmt = msgid_comment_fmt
        self.child_context_fmt = ''
        self.child_comment_fmt = ''
        self.child_items = ()
        self.filter = None
        self.here_text_context_fmt = ''
        self.here_text_comment_fmt = ''
        self.here_text = False
    def match(self, words):
        """Judge the transition to this state."""
        return words[0] == self.keyword
    def get_translatable(self, words, context, comment):
        """Return a tuple or generator of (index of words, context, comment) for all msgids."""
        msgid_context = self.msgid_context_fmt.format(context, *words)
        msgid_comment = self.msgid_comment_fmt.format(comment, *words)
        return ((i, msgid_context, msgid_comment) for i in self.pos)
    def get_child(self, words, context, comment):
        """Return ( (ParseItem, ...), context, comment) for the expected child lines."""
        child_context = self.child_context_fmt.format(context, *words)
        child_comment = self.child_comment_fmt.format(comment, *words)
        return (self.child_items, child_context, child_comment)
    def get_filter(self):
        """Return a instance of _FilterBase for this state."""
        return self.filter
    def has_here_text(self, words, context, comment):
        """Does this state have a here text?"""
        here_text_context = self.here_text_context_fmt.format(context, *words)
        here_text_comment = self.here_text_comment_fmt.format(comment, *words)
        return (self.here_text, here_text_context, here_text_comment)
    def add_child(self, items, child_context_fmt, child_comment_fmt):
        """Add states as expected child lines.

child_context_fmt is used to generate the child context. The child context will be generated by child_context_fmt.format(context, *words).
child_comment_fmt is a variant of the child_context_fmt for comment.
"""
        self.child_items = self.child_items + items
        self.child_context_fmt = child_context_fmt
        self.child_comment_fmt = child_comment_fmt
        return self
    def set_filter(self, filter):
        """Set a instance of _FilterBase for this state."""
        self.filter = filter
        return self
    def mark_here_text(self, here_text_context_fmt, here_text_comment_fmt):
        """Mark the child lines a here text.

here_text_context_fmt is used to generate the child context. The child context will be generated by here_text_context_fmt.format(context, *words).
here_text_comment_fmt is a variant of the here_text_context_fmt for comment.
"""
        self.here_text = True
        self.here_text_context_fmt = here_text_context_fmt
        self.here_text_comment_fmt = here_text_comment_fmt
        return self
class _ParseAnyItem(_ParseItem):
    """A variant of _ParseItem. This instance matchs any lines."""
    def __init__(self, pos = 0, msgid_context_fmt = '', msgid_comment_fmt = ''):
        super().__init__("", pos, msgid_context_fmt, msgid_comment_fmt)
    def match(self, words):
        return True
class _ParseConcatCommentItem(_ParseItem):
    """A variant of _ParseItem. This instance makes a comment from the content of the target line.

The msgid comment will be generated by ' '.join(words) + msgid_comment_fmt + current_comment.
The child comment will be generated by ' '.join(words) + child_comment_fmt + current_comment.
"""
    def __init__(self, keyword, pos = (), msgid_context_fmt = '', msgid_comment_fmt = ''):
        super().__init__(keyword, pos, msgid_context_fmt, msgid_comment_fmt)
    def get_translatable(self, words, context, comment):
        msgid_context = self.msgid_context_fmt.format(context, *words)
        msgid_comment = ' '.join(words) + self.msgid_comment_fmt + comment
        return ((i, msgid_context, msgid_comment) for i in self.pos)
    def get_child(self, words, context, comment):
        child_context = self.child_context_fmt.format(context, *words)
        child_comment = ' '.join(words) + self.child_comment_fmt + comment
        return (self.child_items, child_context, child_comment)
class _ParseConditionPosItem(_ParseItem):
    """A variant of _ParseItem. This instance decides the indices of the msgids by a function (pos_fn) instead of a constant tuple of int."""
    def __init__(self, keyword, pos_fn, msgid_context_fmt = '', msgid_comment_fmt = ''):
        super().__init__(keyword, (), msgid_context_fmt, msgid_comment_fmt)
        self.pos_fn = pos_fn
    def get_translatable(self, words, context, comment):
        self.pos = self.pos_fn(words)
        return super().get_translatable(words, context, comment)
class _ParseConditionKeyItem(_ParseItem):
    """A variant of _ParseItem. This instance decides to transite this state by a function (key_fn) instead of comparing to a constant string."""
    def __init__(self, key_fn, pos = (), msgid_context_fmt = '', msgid_comment_fmt = ''):
        super().__init__('', pos, msgid_context_fmt, msgid_comment_fmt)
        self.key_fn = key_fn
    def match(self, words):
        return self.key_fn(words)
class _ParseLogItem(_ParseItem):
    """A variant of _ParseItem. This instance is specialized in the log nodes."""
    def __init__(self):
        super().__init__('log', (), 'log', '')
    def get_translatable(self, words, context, comment):
        if len(words) == 2:
            cmt = '[log]'
            self.child_comment_fmt = cmt
            return ((1, '', cmt), )
        else:
            cmt = '[log] of {1} "{2}"'.format(*words)
            self.child_comment_fmt = cmt
            return ((1, 'log', cmt), (2, 'log', cmt), (3, '', cmt),)
    def add_child(self, items):
        self.child_items = self.child_items + items
        return self


class _FilterBase:
    """The base class for extracting special strings, such as default plural forms of outfits.

The instance can call the callback function, but it only applies to extracting msgids, doesn't affect the string returned from parser.parse_line().
"""
    def __init__(self, words, indent_number, filename, linenumber, cb):
        """Create a instance from words of the target line."""
        self.words = words
        self.indent_number = indent_number
        self.filename = filename
        self.linenumber = linenumber
        self.cb = cb
    def check(self, words, indent_number):
        """Check the words of a child line."""
        pass
    def filter(self, word, context, comment, filename, linenumber):
        """Filter a msgid."""
        return ((word[0],), context, comment, filename, linenumber)
    def flush(self):
        """Leave the block."""
        pass

class _ConditionVariableFilter(_FilterBase):
    """The filter class for condition nodes.

This filter makes up license and salary names.
"""

    # A condition variable will be translated if it starts with the prefix in this table.
    # A key is the prefix of a variable, a value is the postfix of a msgid.
    _applying_condition_table = {
        'license: ' : ' License',
        'salary: ' : ''
    }
    def is_translate_condition(x):
        for prefix in _ConditionVariableFilter._applying_condition_table.keys():
            if x.startswith(prefix):
                return True
        return False
    def __init__(self, words, indent_number, filename, linenumber, cb):
        super().__init__(words, indent_number, filename, linenumber, cb)
    def filter(self, word, context, comment, filename, linenumber):
        for prefix, postfix in self._applying_condition_table.items():
            if word[0].startswith(prefix):
                return ((word[0][len(prefix):] + postfix,), prefix, comment, filename, linenumber)
        return None

class _GovernmentFilter(_FilterBase):
    """The filter class for government nodes.

This filter makes up the default display name.
"""
    def __init__(self, words, indent_number, filename, linenumber, cb):
        super().__init__(words, indent_number, filename, linenumber, cb)
        self.has_name = False
        self.government_id = words[1]
    def check(self, words, indent_number):
        if words[0] == 'display name':
            self.has_name = True
    def flush(self):
        if not self.has_name:
            self.cb((self.government_id, ), 'government', '[display name] of [government]: ' + self.government_id, self.filename, self.linenumber)

class _LicenseFilter(_FilterBase):
    """The filter class for license nodes.

This filter makes up the license name.
"""
    def __init__(self, words, indent_number, filename, linenumber, cb):
        super().__init__(words, indent_number, filename, linenumber, cb)
    def filter(self, word, context, comment, filename, linenumber):
        return ((word[0] + ' License',), context, comment, filename, linenumber)

class _LogFilter(_FilterBase):
    """The filter class for log nodes.

This filter makes up the sort key.
"""
    def __init__(self, words, indent_number, filename, linenumber, cb):
        super().__init__(words, indent_number, filename, linenumber, cb)
        if len(words) > 2:
            self.count = 0
        else:
            self.count = 2
    def filter(self, word, context, comment, filename, linenumber):
        if self.count <= 1:
            self.cb(word, 'sort key', '[sort key] for ' + comment, filename, linenumber)
        self.count += 1
        return (word, context, comment, filename, linenumber)

class _MissionFilter(_FilterBase):
    """The filter class for mission nodes.

This filter makes up the default name.
"""
    def __init__(self, words, indent_number, filename, linenumber, cb):
        super().__init__(words, indent_number, filename, linenumber, cb)
        self.has_name = False
        self.mission_id = words[1]
    def check(self, words, indent_number):
        if len(words) == 2 and words[0] == 'name':
            self.has_name = True
    def flush(self):
        if not self.has_name:
            self.cb((self.mission_id, ), 'mission', '[name] of [mission]: ' + self.mission_id, self.filename, self.linenumber)

class _OutfitFilter(_FilterBase):
    """The filter class for outfit nodes.

This filter rejects some attributes that won't be displayed and makes up the attribute, label of attribute, sort key, and default plural form.
"""
    # These name is excluded from the (label of) attribute.
    exclusion_from_label = {
        'category' : 1,
        'plural' : 1,
        'flare sprite' : 1,
        'flare sound' : 1,
        'steering flare sprite' : 1,
        'steering flare sound' : 1,
        'afterburner effect' : 1,
        'flotsam sprite': 1,
        'thumbnail' : 1,
        'weapon' : 1,
        'ammo' : 1,
        'description' : 1,
        'licenses' : 1,
    }
    def __init__(self, words, indent_number, filename, linenumber, cb):
        super().__init__(words, indent_number, filename, linenumber, cb)
        self.identifier = ''
        self.plural_name = ''
        self.first = True
        self.first_line_data = None
        self.attributes = []
    def check(self, words, indent_number):
        if len(words) >= 2:
            if words[0] == 'plural':
                self.plural_name = words[1]
    def filter(self, word, context, comment, filename, linenumber):
        if self.first:
            # Outfit Identifier
            self.identifier = word[0]
            self.plural_name = word[0] + 's'
            self.first_line_data = (context, comment, filename, linenumber)
            self.first = False
            return None
        elif context == 'Label of Attribute':
            if word[0] not in self.exclusion_from_label:
                self.attributes.append(((word[0],), 'Attribute', comment, filename, linenumber))
                self.attributes.append(((word[0] + ':',), 'Label of Attribute', comment, filename, linenumber))
            return None
        else:
            return (word, context, comment, filename, linenumber)
    def flush(self):
        self.cb((self.identifier, self.plural_name), *self.first_line_data)
        self.cb((self.plural_name, ), *self.first_line_data)
        for attr in self.attributes:
            self.cb(*attr)
        self.cb((self.identifier, ), 'sort key', '[sort key] for ' + self.first_line_data[1], self.first_line_data[2], self.first_line_data[3])

class _ShipFilter(_FilterBase):
    """The filter class for ship nodes.

This filter makes up the sort key, default noun, and default plural form.
"""
    def __init__(self, words, indent_number, filename, linenumber, cb):
        super().__init__(words, indent_number, filename, linenumber, cb)
        self.need_to_filter = len(words) == 2
        self.identifier = ''
        self.plural_name = ''
        self.noun = None
        self.first = True
        self.first_line_data = None
    def check(self, words, indent_number):
        if len(words) >= 2:
            if words[0] == 'plural':
                self.plural_name = words[1]
            elif words[0] == 'noun':
                self.noun = words[1]
    def filter(self, word, context, comment, filename, linenumber):
        if self.need_to_filter and self.first:
            # Ship Identifier
            self.identifier = word[0]
            self.plural_name = word[0] + 's'
            self.first_line_data = (context, comment, filename, linenumber)
            self.first = False
            return None
        else:
            return (word, context, comment, filename, linenumber)
    def flush(self):
        if self.need_to_filter:
            self.cb((self.identifier, self.plural_name), *self.first_line_data)
            if self.noun is None:
                self.cb(('ship',), self.first_line_data[0], '[noun] of ' + self.first_line_data[1], self.first_line_data[2], self.first_line_data[3])
            self.cb((self.identifier, ), 'sort key', '[sort key] for ' + self.first_line_data[1], self.first_line_data[2], self.first_line_data[3])


# leaf items of parse table
_pi_add = _ParseConditionPosItem(
    'add',
    lambda x: ( 2, ) if x[1] == "description" or x[1] == "spaceport" else (),
    '',
    'add [{2}] of {0}'
)
_pi_apply = _ParseItem('apply')
_pi_assign = _ParseConditionKeyItem(
    lambda x: _ConditionVariableFilter.is_translate_condition(x[0]),
    0,
    'Condition variable',
    '[assign] in {0}'
).set_filter(_ConditionVariableFilter)
_pi_branch = _ParseItem('branch')
_pi_button = _ParseItem('button', 2, '{0}', '[button] in {0}')
_pi_clear = _ParseConditionPosItem(
    'clear',
    lambda x: ( 1, ) if _ConditionVariableFilter.is_translate_condition(x[1]) else (),
    'Condition variable',
    '[{1}] in {0}'
).set_filter(_ConditionVariableFilter)
_pi_conversation_label = _ParseItem('label')
_pi_description = _ParseItem('description', 1, '', '[description] of {0}')
_pi_display_name = _ParseItem('display name', 1, '{0}', '[display name] of {0}')
_pi_goto = _ParseItem('goto')
_pi_interface_label = _ParseItem('label', 1, '{0}', '[label] in {0}')
_pi_illegal = _ParseItem('illegal', 2, '', '[illegal] in {0}')
_pi_model_name = _ParseItem('model name', 1, '{0}', '[model name] of {0}')
_pi_name = _ParseItem('name', 1, '{0}', '[name] of {0}')
_pi_name_cmd = _ParseItem('name')
_pi_noun = _ParseItem('noun', 1, '{0}', '[noun] of {0}')
_pi_outfit_any_attributes = _ParseAnyItem(0, 'Label of Attribute', 'Attribute of {0}')
_pi_scene = _ParseItem('scene')
_pi_set = _ParseConditionPosItem(
    'set',
    lambda x: ( 1, ) if _ConditionVariableFilter.is_translate_condition(x[1]) else (),
    'Condition variable',
    '[{1}] in {0}'
).set_filter(_ConditionVariableFilter)
_pi_spaceport = _ParseConditionPosItem(
    'spaceport',
    lambda x: ( 1, ) if x[1] != "clear" else (),
    '',
    '[spaceport] of {0}'
)
_pi_string = _ParseAnyItem(0, '', '{0}')
_pi_string_with_context = _ParseAnyItem(0, '{0}', '{0}')

# #0 inner items of parse table
_pi_choice = _ParseItem(
    'choice', (), '', ''
).add_child(
    (
        _pi_goto,
        _pi_string_with_context,
    ),
    '{0}', 'a choice of {0}'
)
_pi_licenses = _ParseItem(
    'licenses', (), '', ''
).add_child(
    (
        _pi_string_with_context,
    ),
    'license: ', '[licenses] in {0}'
).set_filter(_LicenseFilter)
_pi_plural = _ParseItem('plural', 1, '{0}', 'plural form of {0}')
_pi_phrase = _ParseItem(
    'phrase', (), '', ''
).mark_here_text('', '[phrase] in {0}')

# #1 inner items of parse table
_pi_ship_attributes = _ParseItem(
    'attributes', (), '', ''
).add_child(
    (
        _pi_licenses,
    ),
    '{0}', '[attributes] of {0}'
)

# common tuple of items
_pt_conversation_body = (
    _pi_apply,
    _pi_branch,
    _pi_choice,
    _pi_conversation_label,
    _pi_name_cmd,
    _pi_scene,
    _pi_string_with_context,
)
_pt_planet_body = (
    _pi_add,
    _pi_description,
    _pi_name,
    _pi_spaceport,
)
_pt_ship_body = (
    _pi_description,
    _pi_model_name,
    _pi_name,
    _pi_noun,
    _pi_plural,
    _pi_ship_attributes,
)

# #2 inner items of parse table
_pi_conversation = _ParseItem(
    'conversation', (), '', ''
).add_child(
    _pt_conversation_body, '{0}', '[conversation] {0}'
)
_pi_dialog = _ParseConditionPosItem(
    'dialog',
    lambda x: () if len(x) <= 1 or x[1] == "phrase" else ( 1, ),
    '',
    '[dialog] {0}'
).add_child(
    (
        _pi_phrase,
        _pi_string,
    ),
    '{0}', '[dialog] {0}'
)
_pi_give = _ParseConditionPosItem(
    'give',
    lambda x: (3, ) if len(x) >= 4 and x[1] == "ship" else (),
    'ship',
    '[ship] {0}'
)
_pi_log = _ParseLogItem().add_child((_pi_string, )).set_filter(_LogFilter)

# #3 inner items of parse table
_pi_ship = _ParseConditionPosItem(
    'ship',
    lambda x: ( 2, ) if len(x) > 2 else ( 1, ),
    'ship',
    '[ship] {0}'
).add_child(
    _pt_ship_body, 'ship', '[ship] {0}'
).set_filter(_ShipFilter)
_pi_ship_in_person = _ParseConditionPosItem(
    'ship',
    lambda x: ( 1, 2 ) if len(x) > 2 else ( 1, ),
    'ship',
    '[ship] in {0}'
).add_child(
    _pt_ship_body, 'ship', '[ship] in {0}'
).set_filter(_ShipFilter)
_pi_blocked = _ParseItem('blocked', 1, '', '[blocked] in {0}')

def _need_to_translate_for_cargo(x):
    # The cargos to be displaced by a concrete commodity name.
    unused = {
        'random' : 1,
        'Food' : 1,
        'Clothing' : 1,
        'Metal' : 1,
        'Plastic' : 1,
        'Equipment' : 1,
        'Medical' : 1,
        'Industrial' : 1,
        'Electronics' : 1,
        'Heavy Metals' : 1,
        'Luxury Goods' : 1,
        'Garbage' : 1,
        'Construction' : 1,
        'Illegal Substances' : 1,
        'Highly Illegal Substances' : 1,
        'Illegal Cargo' : 1,
        'Highly Illegal Cargo' : 1,
   }
    return x not in unused
_pi_cargo = _ParseConditionPosItem(
    'cargo',
    lambda x: ( 1, ) if _need_to_translate_for_cargo(x[1]) else (),
    'cargo',
    '[cargo] in {0}'
).add_child(
    (
        _pi_illegal,
    ),
    '{0}', '[cargo] "{2}" in {0}'
)
_pi_clearance = _ParseItem('clearance', 1, '', '[clearance] in {0}')
_pi_commodity = _ParseItem(
    'commodity', 1, 'commodity', '[commodity] {2} in {0}'
).add_child(
    (
        _pi_name,
        _pi_string_with_context,
    ),
    'commodity', '[commodity] {2} in {0}'
)
_pi_fullname = _ParseItem(
    'fullname', (), '', ''
).add_child(
    (
        _pi_string_with_context,
    ),
    'preferences', '[fullname] in {0}'
)
_pi_government = _ParseItem(
    'government', (), '', ''
).add_child(
    (
        _pi_display_name,
    ),
    'government', 'government "{2}" in {0}'
)
_pi_mission_name = _ParseItem('name', 1, 'mission', '[name] of {0}')
_pi_mission_npc_any = _ParseConcatCommentItem(
    'npc', (), '', ''
).add_child(
    (
        _pi_conversation,
        _pi_dialog,
        _pi_ship,
    ),
    '{0}', ' in '
)
_pi_mission_on_any = _ParseConcatCommentItem(
    'on', (), '', ''
).add_child(
    (
        _pi_assign,
        _pi_clear,
        _pi_conversation,
        _pi_dialog,
        _pi_give,
        _pi_log,
        _pi_set,
    ),
    '{0}', ' in '
)
_pi_news_message = _ParseItem(
    'message', (), '', ''
).mark_here_text('', '[message] of {0}')
_pi_news_name = _ParseItem(
    'name', (), '', ''
).mark_here_text('', '[name] of {0}')
_pi_planet = _ParseItem(
    'planet', 1, 'planet', 'planet "{2}" in {0}'
).add_child(
    _pt_planet_body, 'planet', 'planet "{2}" in {0}'
)
_pi_sprite = _ParseItem('sprite', 1, '{0}', '[sprite] in {0}')

# top level items of parse table
_pi_conversation_lv0 = _ParseItem(
    'conversation', (), '', ''
).add_child(
    _pt_conversation_body, 'conversation: {2}', '[conversation]: "{2}"'
)
_pi_category = _ParseItem(
    'category', (), '', ''
).add_child(
    (
        _pi_string_with_context,
    ),
    'category', '[category]: "{2}"'
)
_pi_event = _ParseItem(
    'event', (), '', ''
).add_child(
    (
        _pi_government,
        _pi_planet,
    ),
    'event', '[event]: "{2}"'
)
_pi_galaxy = _ParseItem(
    'galaxy', (), '', ''
).add_child(
    (
        _pi_sprite,
    ),
    'galaxy', '[galaxy]: "{2}"'
)
_pi_government_lv0 = _ParseItem(
    'government', (), '', ''
).add_child(
    (
        _pi_display_name,
    ),
    'government', '[government]: "{2}"'
).set_filter(_GovernmentFilter)
_pi_help = _ParseItem(
    'help', (), '', ''
).add_child(
    (
        _pi_string,
    ),
    '{0}', '[help]: "{2}"'
)
_pi_landing_message = _ParseItem('landing message', 1, '', '[landing message]')
_pi_interface = _ParseItem(
    'interface', (), '', ''
).add_child(
    (
        _pi_button,
        _pi_interface_label,
    ),
    'interface', '[interface]: "{2}"'
)
_pi_language = _ParseItem(
    'language', (), '', ''
).add_child(
    (
        _pi_fullname,
    ),
    '{0}', '[language]: "{2}"'
)
_pi_minable = _ParseItem(
    'minable', 1, 'minable', '[minable]: "{2}"'
).add_child(
    (
        _pi_name,
    ),
    'minable', '[minable]: "{2}"'
)
_pi_mission = _ParseItem(
    'mission', (), '', ''
).add_child(
    (
        _pi_blocked,
        _pi_cargo,
        _pi_clearance,
        _pi_description,
        _pi_illegal,
        _pi_mission_on_any,
        _pi_mission_npc_any,
        _pi_mission_name,
    ),
    'mission: {2}', '[mission]: "{2}"'
).set_filter(_MissionFilter)
_pi_news = _ParseItem(
    'news', (), '', ''
).add_child(
    (
        _pi_news_name,
        _pi_news_message,
    ),
    'news: {2}', '[news]: "{2}"'
)
_pi_outfit = _ParseItem(
    'outfit', 1, 'outfit', '[outfit]: "{2}"'
).add_child(
    (
        _pi_description,
        _pi_licenses,
        _pi_name,
        _pi_plural,
        _pi_outfit_any_attributes,
    ),
    'outfit', '[outfit]: "{2}"'
).set_filter(_OutfitFilter)
_pi_person = _ParseItem(
    'person', 1, 'person', '[person]'
).add_child(
    (
        _pi_ship_in_person,
        _pi_phrase,
    ),
    'person', '[person]: "{2}"'
)
_pi_phrase_lv0 = _ParseItem(
    'phrase', (), '', ''
).mark_here_text('', '[phrase]: "{2}"')
_pi_planet_lv0 = _ParseItem(
    'planet', 1, 'planet', '[planet]: "{2}"'
).add_child(
    _pt_planet_body, 'planet', '[planet]: "{2}"'
)
_pi_rating = _ParseItem(
    'rating', (), '', ''
).add_child(
    (
        _pi_string_with_context,
    ),
    'rating', '[rating]: "{2}"'
)
_pi_ship_lv0 = _ParseConditionPosItem(
    'ship',
    lambda x: () if len(x) > 2 else ( 1, ),
    'ship',
    '[ship]: "{2}"'
).add_child(
    _pt_ship_body, 'ship', '[ship]: "{2}"'
).set_filter(_ShipFilter)
_pi_start = _ParseItem(
    'start', (), '', ''
).add_child(
    (
        _pi_assign,
        _pi_clear,
        _pi_description,
        _pi_name,
        _pi_set,
    ),
    'start', '[start]'
)
_pi_system = _ParseItem(
    'system', 1, 'system', '[system]: "{2}"'
).add_child(
    (
        _pi_name,
    ),
    'system', '[system]: "{2}"'
)
_pi_tip = _ParseItem(
    'tip', 1, 'Label of Attribute', '[tip]'
).add_child(
    (
        _pi_string,
    ),
    'Label of Attribute', '[tip]: "{2}"'
)
_pi_trade = _ParseItem(
    'trade', (), '', ''
).add_child(
    (
        _pi_commodity,
    ),
    'trade', '[trade]'
)

# top level parse table
_pt_top = (
    _pi_conversation_lv0,
    _pi_category,
    _pi_event,
    _pi_galaxy,
    _pi_government_lv0,
    _pi_help,
    _pi_interface,
    _pi_landing_message,
    _pi_language,
    _pi_minable,
    _pi_mission,
    _pi_news,
    _pi_outfit,
    _pi_person,
    _pi_phrase_lv0,
    _pi_planet_lv0,
    _pi_rating,
    _pi_ship_lv0,
    _pi_start,
    _pi_system,
    _pi_tip,
    _pi_trade,
)

def _choose_quotation(s):
    """choose a quotation mark.

This function must be definitely same algorithm with DataWriter.
"""
    has_space = False
    has_quote = False
    for c in s:
        if 0 <= ord(c) and c <= ' ':
            has_space = True
        if c == '"':
            has_quote = True
    if has_quote:
        return '`'
    elif has_space or len(s) == 0:
        return '"'
    else:
        return ''

class _NodeData:
    """This class has a node data.

This node data is used by Gettext::TranslateNode()."""
    def __init__(self, base_indent_number, first_line_words, context, comment, filename, linenumber):
        """Initialize and record the first line data."""
        self.base_indent_number = int(base_indent_number)
        self.text = ''
        self.append(base_indent_number, first_line_words)
        self.context = context
        self.comment = comment
        self.filename = filename
        self.linenumber = linenumber
    def append(self, indent, words):
        """Append a line data."""
        if words[0].startswith('#'):
            return
        n = int(indent) - self.base_indent_number
        self.text += '\t' * n;
        sep = ''
        for word in words:
            self.text += sep
            q = _choose_quotation(word)
            self.text += q + word + q
            sep = ' '
        self.text += '\n'
    def out(self):
        """Output call back data."""
        return ( (self.text, ), self.context, self.comment, self.filename, self.linenumber)
    def base_indent(self):
        return self.base_indent_number

class _IndentTracker:
    """The class has data according to the indent number."""
    def __init__(self):
        self.indent_number = [ 0 ]
        self.parse_table = [ _pt_top ]
        self.context = [ '' ]
        self.comment = [ '' ]
        self.filter = [ None ]
    def new_indent(self, new_indent):
        if new_indent < 0:
            return
        # None means undetermined indent number. It will be determined at the next line if it has a child node.
        if self.indent_number[-1] is None and self.indent_number[-2] < new_indent:
            self.indent_number[-1] = new_indent
        else:
            while self.indent_number[-1] is None or self.indent_number[-1] > new_indent:
                del self.indent_number[-1]
                del self.parse_table[-1]
                del self.context[-1]
                del self.comment[-1]
                if self.filter[-1] is not None:
                    self.filter[-1].flush()
                del self.filter[-1]
            if self.indent_number[-1] != new_indent:
                if self.parse_table[-1] is not None:
                    raise RuntimeError('Unknown indent.')
    def get_parse_table(self):
        return self.parse_table[-1]
    def get_context(self):
        return self.context[-1]
    def get_comment(self):
        return self.comment[-1]
    def get_filter(self):
        return self.filter[-1]
    def prepare_next_indent(self, child_parse_table, child_context, child_comment, child_filter):
        self.indent_number.append(None)
        self.parse_table.append(child_parse_table)
        self.context.append(child_context)
        self.comment.append(child_comment)
        self.filter.append(child_filter)


class parser:
    """A parser of Endless Sky PO.

You call parse_line(), and the callback function is called by every msgids.
"""
    def __init__(self):
        self.cb = lambda msg, context, comment, filename, linenumber: None
        self.node_data = None
        self.words = []
        self.indent_number = 0
        self.indent_tracker = _IndentTracker();
        self.remainder = ''
    def _output_node_data(self):
        s = self.cb(*self.node_data.out())
        if s is None:
            s = self.node_data.out()[0][0]
        line = s.split('\n')[0:-1]
        ind = '\t' * int(self.node_data.base_indent())
        sep = '\n' + ind
        s = ind + sep.join(line) + '\n'
        self.node_data = None
        return s
    def flush(self):
        """flush internal condition.

You should call this at the end of a file."""
        self.indent_tracker.new_indent(0)
        s = ''
        if self.node_data is not None:
            s = self._output_node_data() + self.remainder
        return s
    def set_callback(self, f):
        """Set callback function.

Its callback function has the paremeters of:
1st: The tuple string of msgid and msgid_plural. If it has no msgid_plural, the tuple size is 1.
2nd: The string of context.
3rd: The string of comment.
4th: The filename.
5th: The number of line.

The return value means the string to replace if it is not None. If None, the
word is not replaced.
"""
        self.cb = f
    def parse_line(self, line, filename, linenumber):
        """parse a line and return the replaced string by the callback function."""
        words, quotations, delims, indent_number = _split_words(line)
        self.words = words
        self.indent_number = indent_number
        return_string = ''
        # Node Data
        if self.node_data is not None:
            if len(words) > 0:
                if self.node_data.base_indent() < indent_number:
                    self.node_data.append(indent_number, words)
                    self.remainder = ''
                    return ''
                else:
                    return_string = self._output_node_data() + self.remainder
            else:
                self.remainder += line
                return ''
        if len(words) == 0:
            return return_string + line
        # indent tracking
        self.indent_tracker.new_indent(indent_number)
        current_filter = self.indent_tracker.get_filter()
        if current_filter is not None:
            current_filter.check(words, indent_number)
        # parse
        pt = self.indent_tracker.get_parse_table()
        ignoring = True
        if pt is not None:
            for pi in pt:
                if pi.match(words):
                    new_filter = self.indent_tracker.get_filter()
                    child_filter = None
                    filter_cls = pi.get_filter()
                    if filter_cls is not None:
                        new_filter = filter_cls(words, indent_number, filename, linenumber, self.cb)
                        child_filter = new_filter
                    current_context = self.indent_tracker.get_context()
                    current_comment = self.indent_tracker.get_comment()
                    msgids = pi.get_translatable(words, current_context, current_comment)
                    for idx, token_context, token_comment in msgids:
                        if idx < len(words):
                            translatable = ((words[idx],), token_context, token_comment, filename, linenumber)
                            if new_filter is not None:
                                translatable = new_filter.filter(*translatable)
                            if translatable is not None:
                                s = self.cb(*translatable)
                                if s is not None:
                                    words[idx] = s
                                    quotations[idx] = _choose_quotation(s)
                    has_here_text, here_text_context, here_text_comment = pi.has_here_text(words, current_context, current_comment)
                    if has_here_text:
                        self.node_data = _NodeData(indent_number, words, here_text_context, here_text_comment, filename, linenumber)
                        return return_string
                    else:
                        # set up inner block information
                        child_pt, child_context, child_comment = pi.get_child(words, current_context, current_comment)
                        self.indent_tracker.prepare_next_indent(child_pt, child_context, child_comment, child_filter)
                    ignoring = False
                    break
        if ignoring:
            # ignore entirely including inner block
            self.indent_tracker.prepare_next_indent(None, None, None, None)
        # generate return string
        s = return_string
        for idx in range(len(words)):
            s += delims[idx] + quotations[idx] + words[idx] + quotations[idx]
        if len(delims)>len(words):
            s += delims[-1]
        return s
