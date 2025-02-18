# Licensed under a 3-clause BSD style license - see LICENSE.rst
import pytest
import numpy as np
from numpy.testing import assert_allclose
from astropy import units as u
from astropy.table import Table
from astropy.time import Time
from gammapy.data.gti import GTI
from gammapy.modeling.models import (
    ConstantTemporalModel,
    ExpDecayTemporalModel,
    GaussianTemporalModel,
    GeneralizedGaussianTemporalModel,
    LightCurveTemplateTemporalModel,
    LinearTemporalModel,
    PowerLawSpectralModel,
    PowerLawTemporalModel,
    SineTemporalModel,
    SkyModel,
)
from gammapy.utils.scripts import make_path
from gammapy.utils.testing import mpl_plot_check, requires_data, requires_dependency


# TODO: add light-curve test case from scratch
# only use the FITS one for I/O (or not at all)
@pytest.fixture(scope="session")
def light_curve():
    path = "$GAMMAPY_DATA/tests/models/light_curve/lightcrv_PKSB1222+216.fits"
    return LightCurveTemplateTemporalModel.read(path)


@requires_data()
def test_light_curve_str(light_curve):
    ss = str(light_curve)
    assert "LightCurveTemplateTemporalModel" in ss


@requires_data()
def test_light_curve_evaluate(light_curve):
    t = Time(59500, format="mjd")
    val = light_curve(t)
    assert_allclose(val, 0.015512, rtol=1e-5)

    t = Time(46300, format="mjd")
    val = light_curve.evaluate(t.mjd, ext=3)
    assert_allclose(val, 0.01551196, rtol=1e-5)


def rate(x, c="1e4 s"):
    c = u.Quantity(c)
    return np.exp(-x / c)


def ph_curve(x, amplitude=0.5, x0=0.01):
    return 100.0 + amplitude * np.sin(2 * np.pi * (x - x0) / 1.0)


def test_time_sampling(tmp_path):
    time = np.arange(0, 10, 0.06) * u.hour

    table = Table()
    table["TIME"] = time
    table["NORM"] = rate(time)
    table.meta = dict(MJDREFI=55197.0, MJDREFF=0, TIMEUNIT="hour")
    temporal_model = LightCurveTemplateTemporalModel(table)

    filename = str(make_path(tmp_path / "tmp.fits"))
    temporal_model.write(path=filename)
    model_read = temporal_model.read(filename)
    assert temporal_model.filename == filename
    assert model_read.filename == filename
    assert_allclose(model_read.table["TIME"].quantity.value, time.value)

    t_ref = "2010-01-01T00:00:00"
    t_min = "2010-01-01T00:00:00"
    t_max = "2010-01-01T08:00:00"

    sampler = temporal_model.sample_time(
        n_events=2, t_min=t_min, t_max=t_max, random_state=0, t_delta="10 min"
    )
    sampler = u.Quantity((sampler - Time(t_ref)).sec, "s")

    assert len(sampler) == 2
    assert_allclose(sampler.value, [12661.65802564, 7826.92991], rtol=1e-5)

    table = Table()
    table["TIME"] = time
    table["NORM"] = np.ones(len(time))
    table.meta = dict(MJDREFI=55197.0, MJDREFF=0, TIMEUNIT="hour")
    temporal_model_uniform = LightCurveTemplateTemporalModel(table)

    sampler_uniform = temporal_model_uniform.sample_time(
        n_events=2, t_min=t_min, t_max=t_max, random_state=0, t_delta="10 min"
    )
    sampler_uniform = u.Quantity((sampler_uniform - Time(t_ref)).sec, "s")

    assert len(sampler_uniform) == 2
    assert_allclose(sampler_uniform.value, [1261.65802564, 6026.9299098], rtol=1e-5)

    temporal_model = ConstantTemporalModel()
    sampler_costant = temporal_model.sample_time(
        n_events=2, t_min=t_min, t_max=t_max, random_state=0
    )
    sampler_costant = u.Quantity((sampler_costant - Time(t_ref)).sec, "s")

    assert len(sampler_costant) == 2
    assert_allclose(sampler_costant.value, [4330.10377559, 3334.04566256], rtol=1e-5)

    temporal_model = ExpDecayTemporalModel(t_ref=Time(t_ref).mjd * u.d)
    sampler_expo = temporal_model.sample_time(
        n_events=2, t_min=t_min, t_max=t_max, random_state=0
    )
    sampler_expo = u.Quantity((sampler_expo.mjd - Time(t_ref).mjd), "d")

    assert sampler_expo.unit == u.d
    assert_allclose(
        sampler_expo.to("s").value, [11824.1055276, 7273.04658336], rtol=1e-8
    )


def test_lightcurve_temporal_model_integral():
    time = np.arange(0, 10, 0.06) * u.hour
    table = Table()
    table["TIME"] = time
    table["NORM"] = np.ones(len(time))
    table.meta = dict(MJDREFI=55197.0, MJDREFF=0, TIMEUNIT="hour")
    temporal_model = LightCurveTemplateTemporalModel(table)

    start = [1, 3, 5] * u.hour
    stop = [2, 3.5, 6] * u.hour
    gti = GTI.create(start, stop, reference_time=Time("2010-01-01T00:00:00"))

    val = temporal_model.integral(gti.time_start, gti.time_stop)
    assert len(val) == 3
    assert_allclose(np.sum(val), 1.0, rtol=1e-5)


def test_constant_temporal_model_evaluate():
    temporal_model = ConstantTemporalModel()
    t = Time(46300, format="mjd")
    val = temporal_model(t)
    assert_allclose(val, 1.0, rtol=1e-5)


def test_constant_temporal_model_integral():
    temporal_model = ConstantTemporalModel()
    start = [1, 3, 5] * u.day
    stop = [2, 3.5, 6] * u.day
    gti = GTI.create(start, stop)
    val = temporal_model.integral(gti.time_start, gti.time_stop)
    assert len(val) == 3
    assert_allclose(np.sum(val), 1.0, rtol=1e-5)


def test_linear_temporal_model_evaluate():
    t = Time(46301, format="mjd")
    t_ref = 46300 * u.d
    temporal_model = LinearTemporalModel(alpha=1.0, beta=0.1 / u.day, t_ref=t_ref)
    val = temporal_model(t)
    assert_allclose(val, 1.1, rtol=1e-5)


def test_linear_temporal_model_integral():
    t_ref = Time(55555, format="mjd")
    temporal_model = LinearTemporalModel(
        alpha=1.0, beta=0.1 / u.day, t_ref=t_ref.mjd * u.d
    )
    start = [1, 3, 5] * u.day
    stop = [2, 3.5, 6] * u.day
    gti = GTI.create(start, stop, reference_time=t_ref)
    val = temporal_model.integral(gti.time_start, gti.time_stop)
    assert len(val) == 3
    assert_allclose(np.sum(val), 1.345, rtol=1e-5)


def test_exponential_temporal_model_evaluate():
    t = Time(46301, format="mjd")
    t_ref = 46300 * u.d
    t0 = 2.0 * u.d
    temporal_model = ExpDecayTemporalModel(t_ref=t_ref, t0=t0)
    val = temporal_model(t)
    assert_allclose(val, 0.6065306597126334, rtol=1e-5)


def test_exponential_temporal_model_integral():
    t_ref = Time(55555, format="mjd")

    temporal_model = ExpDecayTemporalModel(t_ref=t_ref.mjd * u.d)
    start = [1, 3, 5] * u.day
    stop = [2, 3.5, 6] * u.day
    gti = GTI.create(start, stop, reference_time=t_ref)
    val = temporal_model.integral(gti.time_start, gti.time_stop)
    assert len(val) == 3
    assert_allclose(np.sum(val), 0.102557, rtol=1e-5)


def test_gaussian_temporal_model_evaluate():
    t = Time(46301, format="mjd")
    t_ref = 46300 * u.d
    sigma = 2.0 * u.d
    temporal_model = GaussianTemporalModel(t_ref=t_ref, sigma=sigma)
    val = temporal_model(t)
    assert_allclose(val, 0.882497, rtol=1e-5)


def test_gaussian_temporal_model_integral():
    temporal_model = GaussianTemporalModel(t_ref=50003 * u.d, sigma="2.0 day")
    start = [1, 3, 5] * u.day
    stop = [2, 3.5, 6] * u.day
    t_ref = Time(50000, format="mjd")
    gti = GTI.create(start, stop, reference_time=t_ref)
    val = temporal_model.integral(gti.time_start, gti.time_stop)
    assert len(val) == 3
    assert_allclose(np.sum(val), 0.682679, rtol=1e-5)


def test_generalized_gaussian_temporal_model_evaluate():
    t = Time(46301, format="mjd")
    t_ref = 46300 * u.d
    t_rise = 2.0 * u.d
    t_decay = 2.0 * u.d
    eta = 1/2
    temporal_model = GeneralizedGaussianTemporalModel(t_ref=t_ref, t_rise=t_rise, t_decay=t_decay, eta=eta)
    val = temporal_model(t)
    assert_allclose(val, 0.882497, rtol=1e-5)


def test_generalized_gaussian_temporal_model_integral():
    temporal_model = GeneralizedGaussianTemporalModel(t_ref=50003 * u.d, t_rise="2.0 day", t_decay="2.0 day", eta=1/2)
    start = 1 * u.day
    stop = 2 * u.day
    t_ref = Time(50000, format="mjd")
    gti = GTI.create(start, stop, reference_time=t_ref)
    val = temporal_model.integral(gti.time_start, gti.time_stop)
    assert_allclose(val, 0.751594, rtol=1e-5)


def test_powerlaw_temporal_model_evaluate():
    t = Time(46302, format="mjd")
    t_ref = 46300 * u.d
    alpha = -2.0
    temporal_model = PowerLawTemporalModel(t_ref=t_ref, alpha=alpha)
    val = temporal_model(t)
    assert_allclose(val, 0.25, rtol=1e-5)


def test_powerlaw_temporal_model_integral():
    t_ref = Time(55555, format="mjd")
    temporal_model = PowerLawTemporalModel(alpha=-2.0, t_ref=t_ref.mjd * u.d)
    start = 1 * u.day
    stop = 4 * u.day
    gti = GTI.create(start, stop, reference_time=t_ref)
    val = temporal_model.integral(gti.time_start, gti.time_stop)
    assert len(val) == 1
    assert_allclose(np.sum(val), 0.25, rtol=1e-5)

    temporal_model.parameters["alpha"].value = -1
    start = [1, 3, 5] * u.day
    stop = [2, 3.5, 6] * u.day
    gti = GTI.create(start, stop, reference_time=t_ref)
    val = temporal_model.integral(gti.time_start, gti.time_stop)
    print(np.sum(val))
    assert len(val) == 3
    assert_allclose(np.sum(val), 0.411847, rtol=1e-5)


def test_sine_temporal_model_evaluate():
    t = Time(46302, format="mjd")
    t_ref = 46300 * u.d
    omega = np.pi / 4.0 * u.rad / u.day
    temporal_model = SineTemporalModel(amp=0.5, omega=omega, t_ref=t_ref)
    val = temporal_model(t)
    assert_allclose(val, 1.5, rtol=1e-5)


def test_sine_temporal_model_integral():
    t_ref = Time(55555, format="mjd")
    omega = np.pi / 4.0 * u.rad / u.day
    temporal_model = SineTemporalModel(amp=0.5, omega=omega, t_ref=t_ref.mjd * u.d)
    start = [1, 3, 5] * u.day
    stop = [2, 3.5, 6] * u.day
    gti = GTI.create(start, stop, reference_time=t_ref)
    val = temporal_model.integral(gti.time_start, gti.time_stop)
    assert len(val) == 3
    assert_allclose(np.sum(val), 1.08261, rtol=1e-5)


@requires_data()
def test_to_dict(light_curve):

    out = light_curve.to_dict()
    assert out["temporal"]["type"] == "LightCurveTemplateTemporalModel"
    assert "lightcrv_PKSB1222+216.fits" in out["temporal"]["filename"]


@requires_data()
def test_with_skymodel(light_curve):

    sky_model = SkyModel(spectral_model=PowerLawSpectralModel())
    out = sky_model.to_dict()
    assert "temporal" not in out

    sky_model = SkyModel(
        spectral_model=PowerLawSpectralModel(), temporal_model=light_curve
    )
    assert "LightCurveTemplateTemporalModel" in sky_model.temporal_model.tag

    out = sky_model.to_dict()
    assert "temporal" in out


@requires_dependency("matplotlib")
def test_plot_constant_model():
    time_range = [Time.now(), Time.now() + 1 * u.d]
    constant_model = ConstantTemporalModel(const=1)
    with mpl_plot_check():
        constant_model.plot(time_range)
