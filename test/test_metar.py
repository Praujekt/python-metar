"""Test the main Metar Library."""
import warnings
from datetime import datetime, timedelta, timezone

import pytest
import metar
from metar import Metar

# METAR fragments used in tests, below
sta_time = "KEWR 101651Z "
sta_time_mod = "KEWR 101651Z AUTO "
sta_time_wind = "KEWR 101651Z 00000KT "

today = datetime.now(timezone.utc)
tomorrow = today + timedelta(days=1)


def raisesParserError(code):
    """Helper to test the a given code raises a Metar.ParserError."""
    with pytest.raises(Metar.ParserError):
        Metar.Metar(code)


def test_xlate_loc():
    """Test that xlate_loc does the right thing."""
    Metar.debug = True
    report = Metar.Metar(
        "METAR KEWR 111851Z VRB03G19KT 2SM R04R/3000VP6000FT TSRA BR FEW015 "
        "BKN040CB BKN065 OVC200 22/22 A2987 RMK AO2 PK WND 29028/1817 WSHFT "
        "1812 TSB05RAB22 SLP114 FRQ LTGICCCCG TS OHD AND NW-N-E MOV NE "
        "P0013 T02270215"
    )
    mstring = str(report)
    assert mstring.find("thunderstorm overhead") > -1


def test_module():
    """Test that module level things are defined."""
    assert hasattr(metar, "__version__")


def test_issue114_multiplebecominggroups():
    """multiple BECMG (becoming) groups should be possible"""
    code = (
        "METAR WSSS 280900Z 26009KT 180V350 0600 R20R/1900D R20C/1600D +TSRA FEW008 SCT013CB FEW015TCU 24/23 Q1010 "
        "BECMG FM0920 TL0930 3000 TSRA "
        "BECMG FM1000 TL1020 6000 NSW"
    )

    metar = Metar.Metar(code)
    assert metar.decode_completed
    assert len(metar._trend_groups) == 10
    assert metar.trend() == "BECMG FM0920 TL0930 3000 TSRA BECMG FM1000 TL1020 6000 NSW"


@pytest.mark.parametrize("trailstr", ["", "=", "=  "])
def test_issue84_trimequals(trailstr):
    """A trailing = in METAR should not trip up the ingest."""
    code = (
        "KABI 031752Z 30010KT 6SM BR FEW009 OVC036 02/01 A3003 RMK AO2 "
        "SLP176 60001 I%i003 T00170006 10017 21006 56017"
    )
    assert Metar.Metar("%s%s" % (code, trailstr)).decode_completed


@pytest.mark.parametrize("hours", [1, 3, 6])
def test_issue77_ice_accretion(hours):
    """Metar parser supports ice accretion data."""
    report = Metar.Metar(
        (
            "KABI 031752Z 30010KT 6SM BR FEW009 OVC036 02/01 A3003 RMK AO2 "
            "SLP176 60001 I%i003 T00170006 10017 21006 56017"
        )
        % (hours,)
    )
    myattr = "ice_accretion_%ihr" % (hours,)
    assert abs(getattr(report, myattr).value("IN") - 0.03) < 0.001
    assert str(report).find("Ice Accretion") > 0


def test_issue64_cloudkeyerror():
    """Lookup on CLOUD_TYPE should not keyerror."""
    report = Metar.Metar(
        "METAR LOXZ 141420Z 08006KT 20KM VCSH FEW025SC SCT040SC BKN090AC "
        "21/14 Q1015 BECMG SCT090"
    )
    res = report.sky_conditions()
    ans = (
        "a few stratocumulus at 2500 feet; scattered stratocumulus at "
        "4000 feet; broken altocumulus at 9000 feet"
    )
    assert res == ans
    mstring = report.string()
    assert mstring.find("altocumulus") > -1


def test_issue67_precip_text():
    """Check that precip_text is properly defined in present_weather."""
    report = Metar.Metar(
        "METAR FSIA 220100Z AUTO 14014KT 120V180 9999 ///////// " "27/23 Q1010"
    )
    res = report.present_weather()
    assert res == "/////////"


def test_issue40_runwayunits():
    """Check reported units on runway visual range."""
    report = Metar.Metar(
        "METAR KPIT 091955Z COR 22015G25KT 3/4SM R28L/2600FT TSRA OVC010CB "
        "18/16 A2992 RMK SLP045 T01820159"
    )
    res = report.runway_visual_range()
    assert res == "on runway 28L, 2600 feet"
    res = report.runway_visual_range("M")
    assert res == "on runway 28L, 792 meters"

def test_issue107_runwayunits():
    """Check reported units on runway visual range defaulting to meters."""
    report = Metar.Metar(
        "METAR KPIT 091955Z COR 22015G25KT 3/4SM R28L/1500 TSRA OVC010CB "
        "18/16 A2992 RMK SLP045 T01820159"
    )
    res = report.runway_visual_range()
    assert res == "on runway 28L, 1500 meters"
    res = report.runway_visual_range("FT")
    assert res == "on runway 28L, 4921 feet"

@pytest.mark.parametrize("RVR", ["R28L/////", "R28L/////FT", "R28L//////", "R28L/////N"])
def test_issue26_runway_slashes(RVR):
    """Check RVR with slashes decoding."""
    report = Metar.Metar(
        "METAR KPIT 091955Z COR 22015G25KT 3/4SM R28L/2600FT {} TSRA OVC010CB "
        "18/16 A2992 RMK SLP045 T1820160".format(RVR)
    )
    assert len(report.runway) == 1

def test_010_parseType_default():
    """Check default value of the report type."""
    assert Metar.Metar("KEWR").type == "METAR"


def test_011_parseType_legal():
    """Check parsing of the report type."""
    assert Metar.Metar("METAR").type, "METAR"
    assert Metar.Metar("SPECI").type, "SPECI"
    assert Metar.Metar("METAR").correction is None
    assert Metar.Metar("METAR COR").correction == "COR"
    raisesParserError("TAF")


def test_020_parseStation_legal():
    """Check parsing of the station code."""
    assert Metar.Metar("KEWR").station_id == "KEWR"
    assert Metar.Metar("METAR KEWR").station_id == "KEWR"
    assert Metar.Metar("METAR COR KEWR").station_id == "KEWR"
    assert Metar.Metar("BIX1").station_id == "BIX1"
    assert Metar.Metar("K256").station_id == "K256"


def test_021_parseStation_illegal():
    """Check rejection of illegal station codes."""
    raisesParserError("1ABC")
    raisesParserError("METAR METAR")
    raisesParserError("METAR DC")
    raisesParserError("METAR A")
    raisesParserError("kewr")


def test_030_parseTime_legal():
    """Check parsing of the time stamp."""
    report = Metar.Metar("KEWR 101651Z")
    assert report.decode_completed
    assert report.time.day == 10
    assert report.time.hour == 16
    assert report.time.minute == 51
    if today.day > 10 or (today.hour > 16 and today.day == 10):
        assert report.time.month == today.month
    if today.month > 1 or today.day > 10:
        assert report.time.year == today.year


def test_031_parseTime_specify_year():
    """Check that the year can be specified."""
    other_year = 2003

    report = Metar.Metar("KEWR 101651Z", year=other_year)
    assert report.decode_completed
    assert report.time.year == other_year


def test_032_parseTime_specify_month():
    """Check that the month can be specified."""
    last_month = ((today.month - 2) % 12) + 1

    report = Metar.Metar("KEWR 101651Z", month=last_month)
    assert report.decode_completed
    assert report.time.month == last_month


def test_033_parseTime_auto_month():
    """Test assignment of time to previous month."""
    # To test this, we need a date last month that is with a greater day
    # than today, which does not always exist!
    last_month = today.replace(day=1) - timedelta(days=1)
    if last_month.day <= today.day:
        return

    report = Metar.Metar(f"KEWR {last_month.day:02.0f}1651Z")
    assert report.decode_completed
    assert report.time.day == last_month.day
    assert report.time.month == last_month.month
    assert report.time.year == last_month.year


def test_034_parseTime_auto_year():
    """Check that year is adjusted if specified month is in the future."""
    next_month = (today.month % 12) + 1
    last_year = today.year - 1

    report = Metar.Metar("KEWR 101651Z", month=next_month)
    assert report.decode_completed
    assert report.time.month == next_month
    if next_month > 1:
        assert report.time.year == last_year
    else:
        assert report.time.year == today.year


def test_035_parseTime_suppress_auto_month():
    """Check that explicit month suppresses automatic month rollback."""
    next_day = tomorrow.day
    if next_day > today.day:
        last_year = today.year - 1

        timestr = "%02d1651Z" % (next_day)
        report = Metar.Metar("KEWR " + timestr, month=1)
        assert report.decode_completed
        assert report.time.day == next_day
        assert report.time.month == 1
        if today.month > 1:
            assert report.time.year == today.year
        else:
            assert report.time.year == last_year


def test_040_parseModifier_default():
    """Check default 'modifier' value."""
    assert Metar.Metar("KEWR").mod == "AUTO"


def test_041_parseModifier():
    """Check parsing of 'modifier' groups."""
    assert Metar.Metar(sta_time + "AUTO").mod == "AUTO"
    assert Metar.Metar(sta_time + "COR").mod == "COR"


def test_042_parseModifier_nonstd():
    """Check parsing of nonstandard 'modifier' groups."""

    def report(mod_group):
        """(Macro) Return Metar object from parsing the modifier group."""
        return Metar.Metar(sta_time + mod_group)

    assert report("RTD").mod == "RTD"
    assert report("TEST").mod == "TEST"
    assert report("CCA").mod == "CCA"
    assert report("CCB").mod == "CCB"
    assert report("CCC").mod == "CCC"
    assert report("CCD").mod == "CCD"
    assert report("CCE").mod == "CCE"
    assert report("CCF").mod == "CCF"
    assert report("CCG").mod == "CCG"
    assert report("CORR").mod == "COR"
    assert report("FINO").mod == "NO DATA"
    assert report("NIL").mod == "NO DATA"


def test_043_parseModifier_illegal():
    """Check rejection of illegal 'modifier' groups."""
    raisesParserError(sta_time + "auto")
    raisesParserError(sta_time + "CCH")
    raisesParserError(sta_time + "MAN")


def test_140_parseWind():
    """Check parsing of wind groups."""
    report = Metar.Metar(sta_time + "09010KT")
    assert report.decode_completed
    assert report.wind_dir.value() == 90
    assert report.wind_speed.value() == 10
    assert report.wind_gust is None
    assert report.wind_dir_from is None
    assert report.wind_dir_from is None
    assert report.wind() == "E at 10 knots"

    report = Metar.Metar(sta_time + "09010MPS")
    assert report.decode_completed
    assert report.wind_speed.value() == 10
    assert report.wind_speed.value("KMH") == 36
    assert report.wind() == "E at 19 knots"
    assert report.wind("MPS") == "E at 10 mps"
    assert report.wind("KMH") == "E at 36 km/h"

    report = Metar.Metar(sta_time + "09010KMH")
    assert report.decode_completed
    assert report.wind_speed.value() == 10
    assert report.wind() == "E at 5 knots"
    assert report.wind("KMH") == "E at 10 km/h"

    report = Metar.Metar(sta_time + "090010KT")
    assert report.decode_completed
    assert report.wind_dir.value() == 90
    assert report.wind_speed.value() == 10

    report = Metar.Metar(sta_time + "000000KT")
    assert report.decode_completed
    assert report.wind_dir.value() == 0
    assert report.wind_speed.value() == 0
    assert report.wind() == "calm"

    report = Metar.Metar(sta_time + "VRB03KT")
    assert report.decode_completed
    assert report.wind_dir is None
    assert report.wind_speed.value() == 3
    assert report.wind() == "variable at 3 knots"

    report = Metar.Metar(sta_time + "VRB00KT")
    assert report.decode_completed
    assert report.wind() == "calm"

    report = Metar.Metar(sta_time + "VRB03G40KT")
    assert report.decode_completed
    assert report.wind_dir is None
    assert report.wind_speed.value() == 3
    assert report.wind_gust.value() == 40
    assert report.wind_dir_from is None
    assert report.wind_dir_to is None
    assert report.wind() == "variable at 3 knots, gusting to 40 knots"

    report = Metar.Metar(sta_time + "21010G30KT")
    assert report.decode_completed
    assert report.wind() == "SSW at 10 knots, gusting to 30 knots"

    report = Metar.Metar(sta_time + "21010KT 180V240")
    assert report.wind_dir.value() == 210
    assert report.wind_speed.value() == 10
    assert report.wind_gust is None
    assert report.wind_dir_from.value() == 180
    assert report.wind_dir_to.value() == 240
    assert report.wind() == "S to WSW at 10 knots"


def test_141_parseWind_nonstd():
    """Check parsing of nonstandard wind groups."""

    def report(wind_group):
        """(Macro) Return Metar object from parsing the given wind group."""
        return Metar.Metar(sta_time + wind_group)

    assert report("OOOOOKT").wind_speed.value() == 0
    assert report("OOOOOKT").wind() == "calm"

    assert report("09010K").wind_speed.string() == "10 knots"
    assert report("09010T").wind_speed.string() == "10 knots"
    assert report("09010LT").wind_speed.string() == "10 knots"
    assert report("09010KTS").wind_speed.string() == "10 knots"
    # Default wind speed units are knots since US station_id is used
    assert report("09010").wind_speed.string() == "10 knots"

    assert report("VRBOOK").wind_speed.value() == 0
    assert report("VRBOOK").wind() == "calm"

    assert report("///00KT").wind() == "calm"
    assert report("/////KT").wind() == "missing"
    assert report("000//KT").wind() == "missing"
    assert report("/////").wind() == "missing"

    assert report("09010G//KT").wind_gust is None
    assert report("09010GMKT").wind_gust is None
    assert report("09010GMMKT").wind_gust is None
    assert report("09010G7KT").wind_gust.value() == 7

    assert report("MMM00KT").wind() == "calm"
    assert report("MMMMMKT").wind() == "missing"
    assert report("000MMKT").wind() == "missing"
    assert report("MMMMM").wind() == "missing"
    assert report("MMMMMGMMKT").wind() == "missing"
    assert report("MMMMMG01KT").wind() == "missing"


def test_issue139_no_wind_unit():
    """Check the default wind speed units for international sites."""
    report = Metar.Metar("CXXX 101651Z 09010G20")
    assert report.wind_speed.string() == "10 mps"


def test_issue51_strict():
    """Check that setting strict=False prevents a ParserError"""
    with warnings.catch_warnings(record=True) as w:
        report = Metar.Metar(sta_time + "90010KT", strict=False)
    assert len(w) == 1
    assert report.wind_speed is None


def test_142_parseWind_illegal():
    """Check rejection of illegal wind groups."""
    raisesParserError(sta_time + "90010KT")
    raisesParserError(sta_time + "9010KT")
    raisesParserError(sta_time + "09010 KT")
    raisesParserError(sta_time + "09010FPS")
    raisesParserError(sta_time + "09010MPH")
    raisesParserError(sta_time + "00///KT")
    raisesParserError(sta_time + "VAR10KT")
    raisesParserError(sta_time + "21010KT 180-240")
    raisesParserError(sta_time + "123UnME")


def test_150_parseVisibility():
    """Check parsing of visibility groups."""

    def report(vis_group):
        """(Macro) Return Metar object for a report with the vis group."""
        return Metar.Metar(sta_time + "09010KT " + vis_group)

    def report_nowind(vis_group):
        """(Macro) Return Metar object for a report containing the given
        visibility group, without a preceeding wind group.
        """
        return Metar.Metar(sta_time + vis_group)

    assert report("10SM").vis.value() == 10
    assert report("10SM").vis_dir is None
    assert report("10SM").max_vis is None
    assert report("10SM").max_vis_dir is None
    assert report("10SM").visibility() == "10 miles"

    assert report("3/8SM").vis.value() == 0.375
    assert report("3/8SM").vis_dir is None
    assert report("3/8SM").max_vis is None
    assert report("3/8SM").max_vis_dir is None
    assert report("3/8SM").visibility() == "3/8 miles"

    assert report("1 3/4SM").vis.value() == 1.75
    assert report("1 3/4SM").vis_dir is None
    assert report("1 3/4SM").max_vis is None
    assert report("1 3/4SM").max_vis_dir is None
    assert report("1 3/4SM").visibility() == "1 3/4 miles"

    assert report("5000").vis.value() == 5000
    assert report("5000").vis_dir is None
    assert report("5000").visibility() == "5000 meters"
    assert report("5000M").visibility() == "5000 meters"

    assert report_nowind("5000").vis.value() == 5000
    assert report_nowind("1000W 3000").vis.value() == 1000
    assert report_nowind("1000 3000NE").vis.value() == 1000

    assert report("CAVOK").vis.value() == 10000
    assert report("CAVOK").vis_dir is None
    assert report("CAVOK").max_vis is None
    assert report("CAVOK").max_vis_dir is None
    assert report("CAVOK").visibility(), "10000 meters"

    assert report("1000W 3000").vis.value() == 1000
    assert report("1000W 3000").vis_dir.value() == 270
    assert report("1000W 3000").max_vis.value() == 3000
    assert report("1000W 3000").max_vis_dir is None
    assert report("1000W 3000").visibility() == "1000 meters to W; 3000 meters"

    assert report("1000 3000NE").vis.value() == 1000
    assert report("1000 3000NE").vis_dir is None
    assert report("1000 3000NE").max_vis.value() == 3000
    assert report("1000 3000NE").max_vis_dir.value() == 45
    ans = "1000 meters; 3000 meters to NE"
    assert report("1000 3000NE").visibility() == ans

    assert report("5KM").vis.value() == 5
    assert report("5KM").vis_dir is None
    assert report("5KM").visibility() == "5.0 km"

    assert report("5000E").vis.value() == 5000
    assert report("5000E").visibility() == "5000 meters to E"

    assert report("7000NDV").vis.value() == 7000
    assert report("7000NDV").vis_dir is None
    assert report("7000NDV").visibility() == "7000 meters"

    assert report("M1000").vis.value() == 1000
    assert report("M1000").visibility() == "less than 1000 meters"

    assert report("P6000").vis.value() == 6000
    assert report("P6000").visibility() == "greater than 6000 meters"


def test_151_parseVisibility_direction():
    """Check parsing of compass headings visibility groups."""

    def report(vis_group):
        """(Macro) Return Metar object for a report given vis group."""
        return Metar.Metar(sta_time + "09010KT " + vis_group)

    assert report("5000N").vis_dir.compass() == "N"
    assert report("5000N").vis_dir.value() == 0
    assert report("5000NE").vis_dir.compass() == "NE"
    assert report("5000NE").vis_dir.value() == 45
    assert report("5000E").vis_dir.compass() == "E"
    assert report("5000E").vis_dir.value() == 90
    assert report("5000SE").vis_dir.compass() == "SE"
    assert report("5000SE").vis_dir.value() == 135
    assert report("5000S").vis_dir.compass() == "S"
    assert report("5000S").vis_dir.value() == 180
    assert report("5000SW").vis_dir.compass() == "SW"
    assert report("5000SW").vis_dir.value() == 225
    assert report("5000W").vis_dir.compass() == "W"
    assert report("5000W").vis_dir.value() == 270
    assert report("5000NW").vis_dir.compass() == "NW"
    assert report("5000NW").vis_dir.value() == 315


def test_152_parseVisibility_with_following_temperature():
    """Check parsing of visibility groups followed immediately by a group."""

    def report(vis_group):
        """(Macro) Return Metar object for a report given visibility group."""
        return Metar.Metar(sta_time + "09010KT " + vis_group)

    assert report("CAVOK 02/01").vis.value() == 10000
    assert report("CAVOK 02/01").vis_dir is None
    assert report("CAVOK 02/01").max_vis is None
    assert report("CAVOK 02/01").temp.value() == 2.0
    assert report("CAVOK 02/01").dewpt.value() == 1.0

    assert report("5000 02/01").vis.value() == 5000
    assert report("5000 02/01").vis_dir is None
    assert report("5000 02/01").max_vis is None
    assert report("5000 02/01").temp.value() == 2.0
    assert report("5000 02/01").dewpt.value() == 1.0


def test_290_ranway_state():
    """Check parsing of runway state groups."""

    def report(runway_state):
        """(Macro) Return Metar object for  given runway state group"""
        sample_metar = (
            "EGNX 191250Z VRB03KT 9999 -RASN FEW008 SCT024 " "BKN046 M01/M03 Q0989 "
        )
        return Metar.Metar(sample_metar + " " + runway_state)

    assert report("09690692 27550591").temp.value() == -1.0
    assert report("09690692 27550591").remarks() == ""

    assert report("09SNOCLO").remarks() == ""
    assert report("09CLRD//").remarks() == ""

    assert report("R/SNOCLO").remarks() == ""
    assert report("R09/CLRD//").remarks() == ""

    assert report("R01R/SNOCLO ").remarks() == ""


def test_300_parseTrend():
    """Check parsing of trend forecasts."""

    def report(trend_group, remarks=""):
        """(Macro)
        Return Metar object for a report containing the given trend
        forecast and remarks.
        """
        sample_metar = sta_time + "09010KT 10SM -SN OVC020 23/05 Q1001"
        return Metar.Metar(sample_metar + " " + trend_group + " " + remarks)

    assert report("TEMPO FM0306 BKN030CU").trend() == "TEMPO FM0306 BKN030CU"
    assert report("TEMPO FM0306 BKN030CU").temp.value() == 23.0
    assert report("TEMPO FM0306 BKN030CU").remarks() == ""

    assert report("BECMG 0306 VRB06KT").trend() == "BECMG 0306 VRB06KT"
    assert report("FCST AT0327 +FC").trend() == "FCST AT0327 +FC"

    assert report("TEMPO 0306 1/2SM").trend() == "TEMPO 0306 1/2SM"
    ans = "TEMPO FM0306 TL0345 01030G50KT"
    assert report(ans).trend() == ans

    assert report("TEMPO 0306 RMK 402500072").trend() == "TEMPO 0306"
    assert report("TEMPO 0306 RMK 402500072").max_temp_24hr.value() == 25.0


def test_snowdepth():
    """Check parsing of 4/ group snowdepth"""
    sample_metar = (
        "KDOV 040558Z 23004KT 1 1/2SM R01/2800FT -SN BR "
        "OVC006 M01/M01 A3015 RMK AO2A SLP213 P0000 4/001 "
        "60010 T10071007 10017 "
        "21009 55016 VISNO RWY19 CHINO RWY19 $"
    )
    m = Metar.Metar(sample_metar)
    assert m.snowdepth.value() == 1


def test_310_parse_sky_conditions():
    """Check parsing of sky conditions."""

    def report(sky_conditions):
        """(Macro) Return Metar object for the given sky conditions."""
        sample_metar = "{} 14005KT 6000 {} M05/M10 Q1018".format(
            sta_time, sky_conditions
        )
        return Metar.Metar(sample_metar)

    assert report("SCT030").sky_conditions() == "scattered clouds at 3000 feet"
    assert report("BKN001").sky_conditions() == "broken clouds at 100 feet"
    assert report("OVC008").sky_conditions() == "overcast at 800 feet"
    ans = "overcast cumulonimbus at 1000 feet"
    assert report("OVC010CB").sky_conditions() == ans
    ans = "scattered towering cumulus at 2000 feet"
    assert report("SCT020TCU").sky_conditions() == ans
    ans = "broken cumulonimbus at 1500 feet"
    assert report("BKN015CB").sky_conditions() == ans
    ans = "a few clouds at 3000 feet"
    assert report("FEW030").sky_conditions() == ans
    ans = "indefinite ceiling, vertical visibility to 100 feet"
    assert report("VV001").sky_conditions() == ans
    assert report("SKC").sky_conditions() == "clear"
    assert report("CLR").sky_conditions() == "clear"
    assert report("NSC").sky_conditions() == "clear"


def test_not_strict_mode():
    """Test the strict attribute on parsing."""
    # This example metar has an extraneous 'M' in it, but the rest is fine
    # Let's make sure that we can activate a non-strict mode, and flag that
    # there are unparsed portions
    code = "K9L2 100958Z AUTO 33006KT 10SM CLR M A3007 RMK AO2 SLPNO FZRANO $"
    raisesParserError(code)

    with warnings.catch_warnings(record=True) as w:
        report = Metar.Metar(code, strict=False)
    assert len(w) == 1

    assert not report.decode_completed
    assert report.cycle == 10
    assert report.mod == "AUTO"
    assert not report.recent
    assert report.station_id == "K9L2"
    assert report.vis.value() == 10
    assert report.sky_conditions() == "clear"


def test_cor_auto_mod():
    """Test parsing of a COR AUTO Metar."""
    code = (
        "METAR KADW 252356Z COR AUTO 10008KT 10SM CLR 19/11 A2986 "
        "RMK AO2 SLP117 T01880111 10230 20188 50004 $ COR 0007="
    )
    m = Metar.Metar(code, year=2019)

    assert m.mod == 'COR AUTO'


def test_slp_outside_remarks():
    """
    Test parsing of a METAR that lists sea level pressure after the altimeter
    setting instead of in the remarks.
    """

    code = (
        "METAR KCOF 191855Z 18015G22KT 7SM FEW049 SCT300 28/18 A3001 SLP162 "
        "RMK WND DATA ESTMD"
    )
    m = Metar.Metar(code, year=2007)
    m.press_sea_level.value() == 1016.2

def test_wind_after_sky():
    """
    Test parsing of a METAR that lists wind after the sky groups
    """

    code = (
        "METAR KCOF 281855Z FEW029TCU FEW040 SCT250 09008KT 7SM 32/25 A3008 "
        "RMK VIRGA E TCU NE AND DSNT ALQDS SLP186"
    )
    m = Metar.Metar(code, year=2007)

    assert m.wind_dir.value() == 90
    assert m.wind_speed.value() == 8

def test_issue136_temperature():
    raisesParserError("METAR EDDM 022150Z 26006KT CAVOK 201/16")


def test_windshear_runway_identifier():
    code = "METAR EDDH 300720Z WS R23"
    m = Metar.Metar(code, month=1, year=2022)
    assert len(m.windshear) == 1
    assert m.windshear[0] == "23"

    code = "METAR EFHK 151350Z WS RWY22L"
    m = Metar.Metar(code)
    assert len(m.windshear) == 1
    assert m.windshear[0] == "22L"


def test_present_weather_others():
    # PO, sand whirls
    code = "VEIM 301200Z 16007KT 7000 PO SCT018 31/27 Q1007 NOSIG"
    m = Metar.Metar(code, month=8, year=2023)
    assert m.present_weather() == 'sand whirls'

    # SQ, squalls
    code = "VEIM 301200Z 16007KT 7000 SQ SCT018 31/27 Q1007 NOSIG"
    m = Metar.Metar(code, month=8, year=2023)
    assert m.present_weather() == 'squalls'

    # FC, funnel cloud
    code = "VEIM 301200Z 16007KT 7000 FC SCT018 31/27 Q1007 NOSIG"
    m = Metar.Metar(code, month=8, year=2023)
    assert m.present_weather() == 'funnel cloud'

    # SS, sandstorm
    code = "VEIM 301200Z 16007KT 7000 SS SCT018 31/27 Q1007 NOSIG"
    m = Metar.Metar(code, month=8, year=2023)
    assert m.present_weather() == 'sandstorm'

    # DS, dust storm
    code = "VEIM 301200Z 16007KT 7000 DS SCT018 31/27 Q1007 NOSIG"
    m = Metar.Metar(code, month=8, year=2023)
    assert m.present_weather() == 'dust storm'

    # NSW, No significant weather
    code = "VEIM 301200Z 16007KT 7000 NSW SCT018 31/27 Q1007 NOSIG"
    m = Metar.Metar(code, month=8, year=2023)
    assert m.present_weather() == 'no significant weather'


# --------------------------------------------------------------------------
# Flight category (VFR / MVFR / IFR / LIFR)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("code,expected", [
    # 10 SM, CLR — clean VFR.
    (
        "METAR KOAK 050153Z 26008KT 10SM CLR 17/11 A2989 "
        "RMK AO2 SLP121 T01720106",
        "VFR",
    ),
    # 3 SM and 800 ft BKN — vis on the MVFR/IFR boundary but ceiling
    # lands squarely in IFR; the worse value wins.
    (
        "METAR KSFO 051256Z 19012KT 3SM -RA BKN008 OVC015 13/11 A2981 "
        "RMK AO2 SLP098",
        "IFR",
    ),
    # 2 SM and 4000 ft BKN — vis is IFR even though ceiling is VFR.
    (
        "METAR KEWR 111851Z VRB03G19KT 2SM R04R/3000VP6000FT TSRA BR "
        "FEW015 BKN040CB BKN065 OVC200 22/22 A2987 RMK AO2",
        "IFR",
    ),
    # SKC and 10 SM — VFR.
    (
        "METAR KSJC 051755Z 00000KT 10SM SKC 22/08 A2990 "
        "RMK AO2 SLP120",
        "VFR",
    ),
    # 4 SM and 2500 ft BKN — both inputs land in MVFR.
    (
        "METAR KSFO 051556Z 28018G28KT 4SM HZ BKN025 17/09 A2997 "
        "RMK AO2 SLP152",
        "MVFR",
    ),
])
def test_flight_category_reference(code, expected):
    """Reference METARs classify per the FAA category thresholds."""
    assert Metar.Metar(code).flight_category() == expected


def test_flight_category_lifr_ceiling():
    """A sub-500 ft ceiling forces LIFR regardless of visibility."""
    code = (
        "METAR KSFO 051256Z 19012KT 5SM BR OVC003 13/11 A2981 "
        "RMK AO2 SLP098"
    )
    assert Metar.Metar(code).flight_category() == "LIFR"


def test_flight_category_lifr_visibility():
    """Sub-1 SM visibility forces LIFR regardless of ceiling."""
    code = (
        "METAR KSFO 051256Z 19012KT 1/2SM FG BKN040 13/11 A2981 "
        "RMK AO2 SLP098"
    )
    assert Metar.Metar(code).flight_category() == "LIFR"


def test_flight_category_indefinite_ceiling_vv():
    """VV (vertical visibility) is treated as a zero-ft ceiling."""
    code = (
        "METAR KSFO 051256Z 19012KT 1/4SM FG VV002 13/11 A2981 "
        "RMK AO2 SLP098"
    )
    m = Metar.Metar(code)
    assert m.ceiling().value("FT") == 200
    assert m.flight_category() == "LIFR"


def test_flight_category_p6sm_treated_as_above_threshold():
    """``P6SM`` (greater than 6 SM) with clear skies is VFR."""
    code = (
        "METAR KOAK 050153Z 26008KT P6SM CLR 17/11 A2989 "
        "RMK AO2 SLP121"
    )
    m = Metar.Metar(code)
    assert m.flight_category() == "VFR"


def test_ceiling_ignores_few_sct():
    """FEW and SCT layers do not constitute a ceiling."""
    code = (
        "METAR KOAK 050153Z 26008KT 10SM FEW020 SCT040 17/11 A2989 "
        "RMK AO2 SLP121"
    )
    m = Metar.Metar(code)
    assert m.ceiling() is None
    assert m.flight_category() == "VFR"


def test_ceiling_picks_lowest_bkn_ovc():
    """Ceiling is the lowest BKN/OVC layer when multiple are present."""
    code = (
        "METAR KEWR 111851Z 18010KT 6SM FEW015 BKN040 OVC200 22/15 A2987 "
        "RMK AO2"
    )
    m = Metar.Metar(code)
    assert m.ceiling().value("FT") == 4000


def test_flight_category_none_when_no_sky_or_vis():
    """A METAR missing both sky and visibility returns ``None``."""
    # Hand-built minimal report: no vis, no sky. Using strict=False
    # because such a code wouldn't pass strict-mode parsing.
    m = Metar.Metar(
        "METAR KOAK 050153Z 26008KT 17/11 A2989", strict=False
    )
    assert m.flight_category() is None


# --------------------------------------------------------------------------
# Plain-English output
# --------------------------------------------------------------------------

KOAK_VFR = (
    "METAR KOAK 050153Z 26008KT 10SM CLR 17/11 A2989 "
    "RMK AO2 SLP121 T01720106"
)


def test_to_plain_english_header_includes_category_station_time():
    """The header line carries category, station id, and obs time."""
    out = Metar.Metar(KOAK_VFR).to_plain_english()
    header = out.splitlines()[0]
    assert "VFR" in header
    assert "KOAK" in header
    assert "01:53Z" in header


def test_to_plain_english_station_name_optional():
    """When ``station_name`` is supplied, it appears in the header."""
    out = Metar.Metar(KOAK_VFR).to_plain_english(station_name="Oakland Int'l")
    assert "KOAK — Oakland Int'l" in out.splitlines()[0]


def test_to_plain_english_clear_vfr():
    """A clean VFR report has a 'Clear skies, no ceiling.' line and no weather."""
    out = Metar.Metar(KOAK_VFR).to_plain_english()
    assert "Clear skies, no ceiling." in out
    assert "Weather:" not in out
    assert "Altimeter 29.89 inHg." in out
    assert "Sea level pressure 1012.1 hPa." in out


def test_to_plain_english_wind_west_at_8():
    """West wind at 8 knots renders as 'Winds west at 8 knots.'."""
    assert "Winds west at 8 knots." in Metar.Metar(KOAK_VFR).to_plain_english()


def test_to_plain_english_calm_wind():
    """``00000KT`` is reported as 'Winds calm.'."""
    code = "METAR KSJC 051755Z 00000KT 10SM SKC 22/08 A2990 RMK AO2 SLP120"
    assert "Winds calm." in Metar.Metar(code).to_plain_english()


def test_to_plain_english_variable_wind_with_gust():
    """Variable wind with a gust includes 'variable' and a gusting clause."""
    code = (
        "METAR KEWR 111851Z VRB03G19KT 2SM TSRA BR FEW015 BKN040CB BKN065 "
        "OVC200 22/22 A2987 RMK AO2"
    )
    out = Metar.Metar(code).to_plain_english()
    assert "Winds variable at 3 knots, gusting to 19 knots." in out


def test_to_plain_english_ifr_includes_ceiling():
    """An IFR report surfaces a ceiling phrase like 'Ceiling 800 feet.'."""
    code = (
        "METAR KSFO 051256Z 19012KT 3SM -RA BKN008 OVC015 13/11 A2981 "
        "RMK AO2 SLP098"
    )
    out = Metar.Metar(code).to_plain_english()
    assert "IFR" in out.splitlines()[0]
    assert "Ceiling 800 feet." in out
    assert "Weather: light rain." in out


def test_to_plain_english_temp_and_humidity_units():
    """Temp/dewpoint render in both °F and °C with a humidity percent."""
    out = Metar.Metar(KOAK_VFR).to_plain_english()
    # Don't pin the humidity number — formulas differ — but require all parts.
    assert "Temperature 63°F (17°C)" in out
    assert "dewpoint 51°F (11°C)" in out
    assert "%." in out  # humidity present


def test_to_plain_english_station_status_automated():
    """``AO2`` triggers an 'automated (AO2)' status line."""
    assert "Station is automated (AO2)." in (
        Metar.Metar(KOAK_VFR).to_plain_english()
    )


def test_to_plain_english_station_status_sensor_and_maintenance():
    """Sensor flags + a trailing ``$`` produce status lines."""
    code = (
        "METAR KOAK 050153Z 26008KT 10SM CLR 17/11 A2989 "
        "RMK AO1 TSNO PWINO FZRANO RVRNO $"
    )
    out = Metar.Metar(code).to_plain_english()
    assert "Station is automated (AO1)." in out
    assert "TSNO" in out and "PWINO" in out
    assert "FZRANO" in out and "RVRNO" in out
    assert "Station needs maintenance ($)." in out


def test_relative_humidity_known_value():
    """RH at saturated dewpoint (T == Td) should be 100%."""
    # Same temp and dewpoint -> saturation -> 100%.
    code = "METAR KSFO 051256Z 19012KT 3SM -RA BKN008 22/22 A2981 RMK AO2"
    rh = Metar.Metar(code).relative_humidity()
    assert abs(rh - 100.0) < 0.01


def test_relative_humidity_none_when_missing_dewpoint():
    """Missing dewpoint yields ``None`` for relative humidity."""
    m = Metar.Metar(
        "METAR KOAK 050153Z 26008KT 10SM CLR A2989", strict=False
    )
    assert m.relative_humidity() is None


# --------------------------------------------------------------------------
# Crosswind / headwind components
# --------------------------------------------------------------------------

@pytest.mark.parametrize("wind_dir,runway,expected_x,expected_h", [
    # Wind from same direction as the runway heading: pure headwind.
    (360, 360, 0.0, 10.0),
    (90,  90,  0.0, 10.0),
    # Wind from opposite direction: pure tailwind (negative headwind).
    (180, 360, 0.0, -10.0),
    # Wind perpendicular: pure crosswind, no headwind component.
    (90,  360, 10.0, 0.0),    # right crosswind
    (270, 360, 10.0, 0.0),    # left crosswind (sign of magnitude is same)
    # 45-degree quartering wind: equal split (sqrt(2)/2 * 10 ≈ 7.1).
    (45,  360, 7.1, 7.1),
    (315, 360, 7.1, 7.1),     # left-quartering headwind
    (135, 360, 7.1, -7.1),    # right-quartering tailwind
])
def test_wind_components_geometry(wind_dir, runway, expected_x, expected_h):
    """Standard angle cases produce the expected crosswind/headwind split."""
    x, h = Metar.wind_components(wind_dir, 10, runway)
    assert x == expected_x
    assert h == expected_h


def test_wind_components_calm_wind():
    """Zero wind speed produces zero on both components."""
    assert Metar.wind_components(360, 0, 90) == (0.0, 0.0)


def test_wind_components_360_equals_0():
    """``wind_dir=360`` should behave the same as ``wind_dir=0``."""
    a = Metar.wind_components(360, 15, 90)
    b = Metar.wind_components(0, 15, 90)
    assert a == b


def test_wind_components_crosswind_is_nonnegative():
    """Crosswind magnitude must never come back negative."""
    for wind_dir in range(0, 360, 15):
        x, _ = Metar.wind_components(wind_dir, 20, 270)
        assert x >= 0


def test_wind_components_with_parsed_report():
    """Smoke: feed a parsed METAR's wind into the helper."""
    code = "METAR KSFO 051556Z 28018G28KT 4SM HZ BKN025 17/09 A2997 RMK AO2"
    m = Metar.Metar(code)
    # KSFO runway 28L heading is 281°. Wind from 280° at 18 kt — almost
    # straight on, so a strong headwind and a negligible crosswind.
    x, h = Metar.wind_components(
        m.wind_dir.value(), m.wind_speed.value("KT"), 281
    )
    assert h > 17.0
    assert x < 1.0


# --------------------------------------------------------------------------
# Expanded remark coverage (Feature 4)
# --------------------------------------------------------------------------

BASE = "METAR KOAK 050153Z 26008KT 10SM CLR 17/11 A2989 RMK AO2"


@pytest.mark.parametrize("token,attr", [
    ("TSNO", "tsno"),
    ("PWINO", "pwino"),
    ("FZRANO", "fzrano"),
    ("RVRNO", "rvrno"),
    ("FROPA", "fropa"),
    ("PRESRR", "presrr"),
    ("PRESFR", "presfr"),
])
def test_sensor_and_pressure_flags(token, attr):
    """Each flag remark sets its parsed boolean attribute."""
    m = Metar.Metar(BASE + " " + token)
    assert getattr(m, attr) is True


def test_maintenance_flag_at_end_of_report():
    """A trailing ``$`` token sets ``maintenance_needed`` and parses cleanly."""
    m = Metar.Metar(BASE + " $")
    assert m.maintenance_needed is True


def test_virga_without_direction():
    """``VIRGA`` alone sets the boolean but leaves direction None."""
    m = Metar.Metar(BASE + " VIRGA")
    assert m.virga is True
    assert m.virga_dir is None


def test_virga_with_direction():
    """``VIRGA SW`` records the cardinal direction."""
    m = Metar.Metar(BASE + " VIRGA SW")
    assert m.virga is True
    assert m.virga_dir == "SW"


def test_variable_ceiling_cig_remark():
    """``CIG 005V010`` produces 500-1000 ft ceiling-min/max distances."""
    m = Metar.Metar(
        "METAR KOAK 050153Z 26008KT 3SM OVC008 17/11 A2989 RMK AO2 CIG 005V010"
    )
    assert m.ceiling_min.value("FT") == 500
    assert m.ceiling_max.value("FT") == 1000


def test_variable_visibility_vis_remark():
    """``VIS 1V3`` records prevailing-visibility min/max in statute miles."""
    m = Metar.Metar(
        "METAR KOAK 050153Z 26008KT 2SM OVC008 17/11 A2989 RMK AO2 VIS 1V3"
    )
    assert m.vis_var_low.value("SM") == 1
    assert m.vis_var_high.value("SM") == 3


def test_variable_visibility_fractional():
    """Fractional VIS values like ``1/2V2`` parse via the distance class."""
    m = Metar.Metar(
        "METAR KOAK 050153Z 26008KT 1/2SM OVC008 17/11 A2989 RMK AO2 VIS 1/2V2"
    )
    assert m.vis_var_low.value("SM") == 0.5
    assert m.vis_var_high.value("SM") == 2


def test_surface_visibility_remark():
    """``SFC VIS 2`` populates ``surface_vis``."""
    m = Metar.Metar(
        "METAR KOAK 050153Z 26008KT 2SM OVC008 17/11 A2989 RMK AO2 SFC VIS 2"
    )
    assert m.surface_vis.value("SM") == 2


def test_tower_visibility_remark():
    """``TWR VIS 3`` populates ``tower_vis``."""
    m = Metar.Metar(
        "METAR KOAK 050153Z 26008KT 2SM OVC008 17/11 A2989 RMK AO2 TWR VIS 3"
    )
    assert m.tower_vis.value("SM") == 3


def test_station_status_sentence_now_uses_parsed_attrs():
    """The plain-English status line still works after the refactor."""
    code = BASE + " TSNO PWINO FZRANO RVRNO $"
    out = Metar.Metar(code).to_plain_english()
    assert "Station is automated (AO2)." in out
    assert "TSNO" in out and "PWINO" in out
    assert "FZRANO" in out and "RVRNO" in out
    assert "Station needs maintenance ($)." in out
