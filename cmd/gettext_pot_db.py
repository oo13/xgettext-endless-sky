#!/usr/bin/python3
# -*- coding: utf-8-unix -*-
"""Gettext POT database"""
# Copyright © 2018, 2019, 2021 OOTA, Masato
#
# This is published by CC0 1.0.
# For more information, see CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
# at https://creativecommons.org/publicdomain/zero/1.0/deed).

import types
import re

def _id(msg, context):
    if len(context) == 0:
        return msg
    else:
        return context + '\x04' + msg

class pot_db:
    """Gettext POT database"""
    def __init__(self):
        self.messages = [] # in order
        self.contexts = [] # in order
        self.message_info = [] # in order
        self.message_index = {}
    def append(self, msg, context, comment, file, line):
        """append message data."""
        if msg[0] == '':
            return
        id = _id(msg[0], context)
        if id not in self.message_index:
            self.message_index[id] = len(self.messages)
            self.messages.append(msg)
            self.contexts.append(context)
            self.message_info.append([ (comment, file, line) ])
        else:
            idx = self.message_index[id]
            self.message_info[idx].append( (comment, file, line) )
            if len(self.messages[idx]) < len(msg):
                self.messages[idx] = msg
    _escape_table = {
        '\a' : '\\a',
        '\b' : '\\b',
        '\f' : '\\f',
        '\n' : '\\n"\n"',
        '\r' : '\\r',
        '\t' : '\\t',
        '\v' : '\\v',
        '\\' : '\\\\',
        '"' : '\\"'
    }
    def _escape_chars(self, s):
        """escape character for gettext."""
        out = ''
        found_nl = False
        for c in s:
            found_nl |= c == '\n'
            if c in self._escape_table:
                out += self._escape_table[c]
            elif c < ' ':
                out += '\\x{0:02X}'.format(ord(c))
            else:
                out += c
        if s[-1] == '\n':
            out = out[:-3]
        if found_nl:
            out = '"\n"' + out
        return out
    def write(self, write_func):
        """write all message data."""
        for idx in range(len(self.messages)):
            write_func("\n")
            for info in self.message_info[idx]:
                if len(info[0]) > 0:
                    write_func("#. " + info[0] + "\n")
            write_func("#:")
            for info in self.message_info[idx]:
                write_func(" {}:{}".format(info[1], info[2]))
            write_func("\n")
            if len(self.contexts[idx]) > 0:
                write_func('msgctxt "{}"\n'.format(self._escape_chars(self.contexts[idx])))
            if len(self.messages[idx]) == 1:
                write_func('msgid "{}"\n'.format(self._escape_chars(self.messages[idx][0])))
                write_func('msgstr ""\n')
            else:
                write_func('msgid "{}"\n'.format(self._escape_chars(self.messages[idx][0])))
                write_func('msgid_plural "{}"\n'.format(self._escape_chars(self.messages[idx][1])))
                write_func('msgstr[0] ""\n')
