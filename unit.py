import re
from typing import List, Union, Optional, Generator, TypeVar, Iterable, Iterator

from . import LineInterface, Comment as oldComment, LineError, NoOptionError, UnitBase


class NoSectionError(Exception):
    """Исключение, возникающее при отсутствующей секции."""

    def __init__(self, section: str):
        super().__init__('No section: {!r}'.format(section))


class DuplicateSectionError(Exception):
    """Исключение, возникающее если секция существует."""

    def __init__(self, section: str):
        super().__init__('Section already exists: {!r}'.format(section))


# noinspection PyClassHasNoInit
class Comment(oldComment):
    COMMENT_CHARS = ('#', ';')


OptionType = TypeVar('OptionType', bound='Option')


class Option(LineInterface):
    """Класс линии опции."""
    DELIMITER_CHAR = '='
    DELIMITER_CHARS = (DELIMITER_CHAR, ':')
    _TMPL = r"""
        (?P<option>.*?)
        \s*(?P<vi>[{delim}])\s*
        (?P<name>.*)$
    """
    _PATTERN = re.compile(_TMPL.format(delim=''.join(DELIMITER_CHARS)), re.VERBOSE)

    BOOLEAN_STATES = {'1': True, '0': False,
                      'yes': True, 'no': False,
                      'true': True, 'false': False,
                      'on': True, 'off': False}
    BOOLEAN_STR = ('no', 'yes')

    name: str
    value: List[str] = None

    @classmethod
    def test(cls, line: str) -> bool:
        return bool(cls._PATTERN.match(line))

    def __init__(self, line: str, value: List[str] = None, *, test: bool = False):
        """
        :raise: LineError
        """
        self.value = []  # type: List[str]
        if not self.test(line):
            if test:
                raise LineError
            assert value
            self.name = line  # type: str
            self.value.extend(value)
            return

        mo = self._PATTERN.match(line)
        self.name, value = mo.group('option', 'name')  # type: str, str
        self.value.append(value)

    def __repr__(self) -> str:
        return '{}({}{}{!r})'.format(self.__class__.__name__, self.name, self.DELIMITER_CHAR, self.value)

    def __str__(self) -> str:
        return '\n'.join(map(lambda x: '{}{}{}'.format(self.name, self.DELIMITER_CHAR, self._from_type(x)),
                             self.value)) + '\n'

    @classmethod
    def _from_type(cls, value: Union[str, bool, int, float]) -> str:
        if isinstance(value, bool):
            value = cls.BOOLEAN_STR[int(value)]
        elif isinstance(value, int):
            value = '{:d}'.format(value)
        elif isinstance(value, float):
            value = '{:f}'.format(value)
        return str(value)

    def __add__(self, other: OptionType):
        for value in other.value:
            if value not in self.value:
                self.value.append(value)
        return self


class Section(LineInterface):
    """Класс линии секции."""

    _lines: List[Union[Option, Comment]]
    name: str = None

    @classmethod
    def test(cls, line: str) -> bool:
        line = line.strip()
        return line.startswith('[') and line.endswith(']')

    def __init__(self, line: Optional[str], *, test: bool = False):
        """
        :raise: LineError
        """
        self._lines = []  # type: List[Union[Option, Comment]]

        if line is None:
            return

        if not self.test(line):
            if test:
                raise LineError
            self.name = line
            return

        self.name = line.strip().strip('[]')  # type: str

    def __repr__(self) -> str:
        return '{}({!r} {!r})'.format(self.__class__.__name__, self.name, self._lines)

    def __str__(self) -> str:
        text = ''.join(map(lambda x: str(x), self._lines)) + '\n'
        if self.name:
            return '[{}]\n{}'.format(self.name, text)
        return text

    def __bool__(self) -> bool:
        if self.name is None:
            return bool(self._lines)
        return True

    def append(self, token: Union[Option, Comment], option_name: str = None, before: bool = True):
        index = None
        option = None

        if option_name is not None:
            index = self._lines.index(self.get(option_name))
            if not before:
                index += 1

        if isinstance(token, Option):
            try:
                option = self.get(token.name)
            except NoOptionError:
                pass
            else:
                index = self._lines.index(option)

        if index is None:
            self._lines.append(token)
        else:
            if option:
                self._lines[index] += token
            else:
                self._lines.insert(index, token)

    @property
    def comments(self) -> Generator[Comment, None, None]:
        return (x for x in self._lines if isinstance(x, Comment))

    @property
    def options(self) -> Generator[Option, None, None]:
        return (x for x in self._lines if isinstance(x, Option))

    def get(self, option_name: str) -> Option:
        """
        :raise: NoOptionError
        """
        for value in self.options:
            if value.name == option_name:
                return value
        raise NoOptionError(option_name)

    def remove(self, token: Union[Option, Comment]):
        self._lines.remove(token)


class Unit(UnitBase):
    """Класс парсера ini файла."""

    _lines: List[Section]

    def __init__(self):
        super().__init__()
        self._lines = [Section(None)]

    def read(self, lines: Iterable[str]):
        sections = {}
        section_cur = self.get()

        # Определяем тип строки.
        for line in self._line_split_backslash(lines):
            token = self.__line_to_type(line)
            if token is None:
                pass

            elif isinstance(token, Section):
                try:
                    section_cur = sections[token.name]
                except KeyError:
                    section_cur = token
                    sections[token.name] = section_cur
                    self.append(section_cur)
            else:
                section_cur.append(token)

    @staticmethod
    def __line_to_type(line: str) -> Union[Comment, Option, Section, None]:
        if not line:
            return

        try:
            token = Comment(line, test=True)
        except LineError:
            try:
                token = Section(line, test=True)
            except LineError:
                try:
                    token = Option(line, test=True)
                except LineError:
                    token = Comment(line)
        return token

    @staticmethod
    def is_token(line: str) -> bool:
        return bool(Comment.test(line) or Section.test(line) or Option.test(line))

    def _line_split_backslash(self, lines: Iterable[str]) -> Generator[str, None, None]:
        line_save = ''
        for line in lines:
            line = line.strip()

            if not line_save:
                if not line:
                    pass
                elif line[-1] == '\\':
                    line_save = line[:-1]
                else:
                    yield line
                continue

            if not line:
                yield line_save
                line_save = ''
            elif line[-1] == '\\':
                line = line[:-1]
                if self.is_token(line):
                    yield line_save
                    line_save = line
                else:
                    line_save += ' ' + line
            elif self.is_token(line):
                yield line_save
                line_save = line
            else:
                line_save += ' ' + line
                yield line_save
                line_save = ''

        if line_save:
            yield line_save

    @property
    def sections(self) -> Iterator[str]:
        return map(lambda x: x.value, self._lines)

    def get(self, section_name: Optional[str] = None) -> Section:
        """
        :raise: NoSectionError
        """
        for value in self._lines:
            if value.name == section_name:
                return value
        raise NoSectionError(section_name)

    def remove(self, section: Section):
        self._lines.remove(section)

    def append(self, section_new: Section, section: Optional[Section] = None, before: bool = False):
        """
        :raise: DuplicateSectionError
        """
        try:
            self.get(section_new.name)
        except NoSectionError:
            pass
        else:
            raise DuplicateSectionError(section_new.name) from None

        index = None

        if section_new.name is None:
            index = 0
        elif section is not None:
            index = self._lines.index(section)
            if not before:
                index += 1

        if index is None:
            self._lines.append(section_new)
        else:
            self._lines.insert(index, section_new)
