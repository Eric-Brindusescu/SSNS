from pydantic import BaseModel, Field


class WindInfo(BaseModel):
    direction_deg: int | float | None = None
    speed_kt: int | float | None = None
    gust_kt: int | float | None = None
    variable: bool | None = None


class CloudLayer(BaseModel):
    cover: str | None = None
    code: str | None = None
    text: str | None = None
    type: str | None = None
    base_ft: int | float | None = None
    base_m: int | float | None = None
    altitude_ft: int | float | None = None
    modifier: str | None = None


class VisibilityInfo(BaseModel):
    value: int | float | None = None
    miles: float | None = None
    meters: float | None = None
    unit: str | None = None


class AltimeterInfo(BaseModel):
    value: float | None = None
    hpa: float | None = None
    unit: str | None = None


class ParsedMetar(BaseModel):
    raw: str | None = None
    time: str | None = None
    wind: WindInfo | None = None
    visibility: VisibilityInfo | None = None
    visibility_sm: float | None = None
    temperature_c: float | None = None
    dewpoint_c: float | None = None
    altimeter: AltimeterInfo | None = None
    altimeter_hpa: float | None = None
    humidity_pct: float | None = None
    wx_string: str | None = None
    wx_codes: list[str] | None = None
    sky_cover: str | None = None
    clouds: list[CloudLayer] = Field(default_factory=list)
    flight_category: str | None = None
    flight_rules: str | None = None
    ceiling_ft: int | float | None = None
    elevation_m: float | None = None
    remarks: str | None = None
    translate: dict | None = None
    summary: str | None = None
    error: str | None = None


class TafForecast(BaseModel):
    from_time: str | None = Field(None, alias="from")
    to_time: str | None = Field(None, alias="to")
    start_time: str | None = None
    end_time: str | None = None
    change_indicator: str | None = None
    wind: WindInfo | None = None
    wind_dir_deg: int | float | None = None
    wind_speed_kt: int | float | None = None
    wind_gust_kt: int | float | None = None
    visibility: VisibilityInfo | None = None
    visibility_sm: float | None = None
    visibility_miles: float | None = None
    wx_string: str | None = None
    wx_codes: list[str] | None = None
    sky_cover: str | None = None
    clouds: list[CloudLayer] = Field(default_factory=list)
    flight_rules: str | None = None

    model_config = {"populate_by_name": True}


class ParsedTaf(BaseModel):
    raw: str | None = None
    time: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    remarks: str | None = None
    forecasts: list[TafForecast] = Field(default_factory=list)
    error: str | None = None


class StationInfo(BaseModel):
    name: str | None = None
    icao: str | None = None
    iata: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float | None = None
    status: str | None = None


class SourceWeather(BaseModel):
    source: str = Field(..., description="Data source name")
    station: StationInfo | None = None
    metar: ParsedMetar | None = None
    taf: ParsedTaf | None = None
    error: str | None = None


class WeatherResponse(BaseModel):
    icao: str = Field(..., description="Requested ICAO code")
    sources: list[SourceWeather] = Field(default_factory=list)
