"""
TODO(bootcamper): write the tests for ``src/waypoint_utils.py`` in here.

The example below covers files that parse fine: with and without ``home``,
and files with comments and blank lines in them. The rest is yours:

- Bad data: a file whose top level isn't a mapping, waypoints missing
  ``lat``, ``lon``, or ``alt``, values that aren't numbers, YAML that
  doesn't parse, and a file that isn't there.
- Out of range: latitudes past +/-90 and longitudes past +/-180 get
  rejected.
- Nothing to work with: an empty file, an empty ``waypoints`` list, and
  ``sort_clockwise_sweep`` given a list of 0 or 1 waypoints.
- ``east_north_coordinate_offset_m``: offsets you worked out yourself,
  compared with ``pytest.approx``. Never use ``==`` on meters.
- Ordering: with no ``home``, ``sort_clockwise_sweep`` goes clockwise
  starting from north.
- With a ``home``: the order starts in home's direction instead, and goes
  back to starting at north if home is right on top of the centroid.
- Two waypoints in the same direction: the closer one comes first.
- Parsing gives you frozen ``Coordinate`` objects that can't be changed.

Graded by ``warg run utils grade-tests``: pass on the real code, 90% branch
coverage, and fail on every broken copy in ``grader/mutants/``.
"""

import pytest

from src.types import Coordinate
from src.waypoint_utils import (
    east_north_coordinate_offset_m,
    parse_waypoints_file,
    sort_clockwise_sweep,
)

# The helper and the test below are given to you.


def write_to_tmp_waypoints_file(tmp_path, text):
    """Write ``text`` to a YAML file and hand back its path.

    ``tmp_path`` is a pytest fixture: a fresh empty directory per test.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text(text)
    return path


# One test, three files. ``parametrize`` runs the test body once per
# ``(text, expected)`` pair, and ``ids`` names each run so a failure tells you
# which file broke.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            """
            home: {lat: 1, lon: 2, alt: 3}
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            """
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
              - {lat: 7, lon: 8, alt: 9}
            """,
            (None, [Coordinate(4, 5, 6), Coordinate(7, 8, 9)]),
        ),
        (
            """
            # a lap

            home: {lat: 1, lon: 2, alt: 3}

            waypoints:
              # first leg
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            "",
            (None, []),
        ),
    ],
    ids=["home-and-waypoints", "no-home", "comments-and-blank-lines", "empty-file"],
)
def test_parse_waypoints_file_success(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected


@pytest.mark.parametrize(
    "text",
    [
        """
        waypoints:
          - {lat: 90.1, lon: 0, alt: 0}
        """,
        """
        waypoints:
          - {lat: -90.1, lon: 0, alt: 0}
        """,
        """
        waypoints:
         - {lat: 0, lon: 180.1, alt: 0}
        """,
        """
        waypoints:
          - {lat: 0, lon: -180.1, alt: 0}
        """
    ],
    ids=["lat-too-high", "lat-too-low", "lon-too-high", "lon-too-low"],
)
def test_parse_waypoints_file_out_of_range(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError, match="out of range"):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "text",
    [
        """
        waypoints:
          - {lat: a, lon: b, alt: c}
        """,
    ],
    ids=["non-numeric-values"],
)
def test_parse_waypoints_file_non_numeric(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError, match="non-numeric"):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "text",
    [
        """
        waypoints:
          - {lon: 0, alt: 0}
        """,
        """
        waypoints:
          - {lat: 0, alt: 0}
        """,
        """
        waypoints:
         - {lat: 0, lon: 0}
        """,
    ],
    ids=["lat-missing", "lon-missing", "alt-missing"],
)
def test_parse_waypoints_file_missing_key(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError, match="missing key"):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "text",
    [
        """
        waypoints:
          - {lat: a, lon: b, alt: c
        """,
    ],
    ids=["invalid-yaml"],
)
def test_parse_waypoints_file_invalid_yaml(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError, match="invalid YAML"):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "text",
    [
        """
        hi
        """,
    ],
    ids=["top-level-not-mapping"],
)
def test_parse_waypoints_file_top_level_not_mapping(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError, match="expected a mapping with"):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "text",
    [
        """
        waypoints: 5
        """,
    ],
    ids=["non-list-waypoints"],
)
def test_parse_waypoints_file_non_list(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError, match="must be a list"):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "text",
    [
        """
        waypoints:
         - 5
        """,
    ],
    ids=["non-mapping-waypoint"],
)
def test_parse_waypoints_file_non_mapping(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    with pytest.raises(ValueError, match="must be a mapping with "):
        parse_waypoints_file(path)


def test_sort_clockwise_sweep_no_home_starts_north():
    north = Coordinate(1, 0, 0)
    east = Coordinate(0, 1, 0)
    south = Coordinate(-1, 0, 0)
    west = Coordinate(0, -1, 0)

    result = sort_clockwise_sweep([south, west, east, north])

    assert result == [north, east, south, west]


@pytest.mark.parametrize(
    ("from_lat", "from_lon", "to_lat", "to_lon", "expected_east", "expected_north"),
    [
        (0, 0, 1, 0, 0, 111_195.08),
    ],
    ids=["due-north"],
)
def test_east_north_coordinate_offset_m(from_lat, from_lon, to_lat, to_lon, expected_east, expected_north):
    east, north = east_north_coordinate_offset_m(from_lat, from_lon, to_lat, to_lon)

    assert east == pytest.approx(expected_east, abs=0.01)
    assert north == pytest.approx(expected_north, abs=0.01)


@pytest.mark.parametrize(
    ("from_lat", "from_lon", "to_lat", "to_lon", "expected_east", "expected_north"),
    [
        (60, 0, 60, 1, 55597.54, 0),
    ],
    ids=["due-east"],
)
def test_east_north_coordinate_east_offset(from_lat, from_lon, to_lat, to_lon, expected_east, expected_north):
    east, north = east_north_coordinate_offset_m(from_lat, from_lon, to_lat, to_lon)

    assert east == pytest.approx(expected_east, abs=0.01)
    assert north == pytest.approx(expected_north, abs=0.01)


def test_sort_clockwise_sweep_no_waypoints():

    result = sort_clockwise_sweep([])

    assert result == []


def test_sort_clockwise_sweep_home_waypoints():
    north = Coordinate(1, 0, 0)
    east = Coordinate(0, 1, 0)
    south = Coordinate(-1, 0, 0)
    west = Coordinate(0, -1, 0)
    home = Coordinate(0, 1, 0)

    result = sort_clockwise_sweep([south, west, east, north], home)

    assert result == [east, south, west, north]


def test_sort_clockwise_sweep_tie_braker():
    near = Coordinate(1, 0, 0)
    far = Coordinate(2, 0, 0)
    balance = Coordinate(-3, 0, 0)

    result = sort_clockwise_sweep([far, near, balance])

    assert result == [near, far, balance]