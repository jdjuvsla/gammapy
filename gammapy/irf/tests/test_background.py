# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import absolute_import, division, print_function, unicode_literals
import pytest
import numpy as np
from numpy.testing import assert_allclose, assert_equal
from astropy.tests.helper import assert_quantity_allclose
import astropy.units as u
from astropy.units import Quantity
from ...utils.testing import requires_dependency, requires_data
from ..background import Background3D, Background2D
from ...utils.energy import EnergyBounds

@pytest.fixture(scope='session')
def bkg_3d():
    """A simple Background2D test case"""
    energy = [0.1, 10, 1000] * u.TeV
    det_x = [0, 1, 2, 3] * u.deg
    det_y = [0, 1, 2, 3] * u.deg
    data = np.zeros((2, 3, 3)) * u.Unit('s-1 MeV-1 sr-1')
    data.value[1, 0, 0] = 2
    data.value[1, 1, 1] = 4
    return Background3D(
        energy_lo=energy[:-1], energy_hi=energy[1:],
        detx_lo=det_x[:-1], detx_hi=det_x[1:], dety_lo=det_y[:-1], dety_hi=det_y[1:],
        data=data
    )


@requires_dependency('scipy')
@requires_data('gammapy-extra')
def test_background_3d_basics(bkg_3d):
    assert 'NDDataArray summary info' in str(bkg_3d.data)

    axis = bkg_3d.data.axis('energy')
    assert axis.nbins == 2
    assert axis.unit == 'TeV'

    axis = bkg_3d.data.axis('detx')
    assert axis.nbins == 3
    assert axis.unit == 'deg'

    axis = bkg_3d.data.axis('dety')
    assert axis.nbins == 3
    assert axis.unit == 'deg'

    data = bkg_3d.data.data
    assert data.shape == (2, 3, 3)
    assert data.unit == u.Unit('s-1 MeV-1 sr-1')


def test_background_3d_read_write(tmpdir, bkg_3d):
    filename = str(tmpdir / "bkg3d.fits")
    bkg_3d.to_fits().writeto(filename)

    bkg_3d_2 = Background3D.read(filename)

    axis = bkg_3d_2.data.axis('energy')
    assert axis.nbins == 2
    assert axis.unit == 'TeV'

    axis = bkg_3d_2.data.axis('detx')
    assert axis.nbins == 3
    assert axis.unit == 'deg'

    axis = bkg_3d_2.data.axis('dety')
    assert axis.nbins == 3
    assert axis.unit == 'deg'

    data = bkg_3d_2.data.data
    assert data.shape == (2, 3, 3)
    assert data.unit == 's-1 MeV-1 sr-1'


@requires_dependency('scipy')
def test_background_3d_evaluate(bkg_3d):
    # Evaluate at nodes in energy
    res = bkg_3d.evaluate(detx=np.array([1, 0.5]) * u.deg, dety=np.array([1, 0.5]) * u.deg,
                          energy_reco=np.ones(2) * 1 * u.TeV)
    assert_allclose(res.value, 0)
    assert res.shape == (2,)
    assert res.unit == 's-1 MeV-1 sr-1'

    res = bkg_3d.evaluate(detx=np.array([1, 0.5]) * u.deg, dety=np.array([1, 0.5]) * u.deg,
                          energy_reco=np.ones(2) * 100 * u.TeV)
    assert_allclose(res.value, [1.5, 2])

    detx = np.array(([1, 0.5], [1, 0.5])) * u.deg
    dety = np.array(([1, 0.5], [1, 0.5])) * u.deg
    energy_reco = np.array(([1, 1], [100, 100])) * u.TeV
    res = bkg_3d.evaluate(detx=detx, dety=dety, energy_reco=energy_reco)
    assert_allclose(res.value, [[0, 0], [1.5, 2]])
    assert res.shape == (2, 2)


@requires_dependency('scipy')
def test_background_3d_integrate(bkg_3d):
    """
    energy_band = EnergyBounds([0.1, 10] * u.TeV)
    res = bkg_3d.integrate_on_energy_range(detx=np.array([0.5]) * u.deg, dety=np.array([0.5]) * u.deg,
                                           energy_range=energy_band, n_integration_bins=1)
    assert_quantity_allclose(res, Quantity(0, "1 / (MeV s sr)") * energy_band.bands)
    """

    energy_band = EnergyBounds([10, 1000] * u.TeV)
    res = bkg_3d.integrate_on_energy_range(detx=np.array([0.5]) * u.deg, dety=np.array([0.5]) * u.deg,
                                           energy_range=energy_band, n_integration_bins=1)
    assert 2=3
    assert_quantity_allclose(res[0], Quantity(2, "1 / (MeV s sr)") * energy_band.bands)



@pytest.fixture(scope='session')
def bkg_2d():
    """A simple Background2D test case"""
    energy = [0.1, 10, 1000] * u.TeV
    offset = [0, 1, 2, 3] * u.deg
    data = np.zeros((2, 3)) * u.Unit('s-1 MeV-1 sr-1')
    data.value[1, 0] = 2
    data.value[1, 1] = 4
    return Background2D(
        energy_lo=energy[:-1], energy_hi=energy[1:],
        offset_lo=offset[:-1], offset_hi=offset[1:],
        data=data,
    )


@requires_dependency('scipy')
def test_background_2d_evaluate(bkg_2d):
    # TODO: the test cases here can probably be improved a bit
    # There's some redundancy, and no case exactly at a node in energy

    # Evaluate at log center between nodes in energy
    res = bkg_2d.evaluate(fov_offset=[1, 0.5] * u.deg, energy_reco=1 * u.TeV)
    assert_allclose(res.value, 0)
    assert res.shape == (2,)
    assert res.unit == 's-1 MeV-1 sr-1'

    res = bkg_2d.evaluate(fov_offset=[1, 0.5] * u.deg, energy_reco=100 * u.TeV)
    assert_allclose(res.value, [3, 2])

    res = bkg_2d.evaluate(fov_offset=[1, 0.5] * u.deg, energy_reco=[1, 100] * u.TeV)
    assert_allclose(res.value, [[0, 0], [3, 2]])
    assert res.shape == (2, 2)

    res = bkg_2d.evaluate(fov_offset=1 * u.deg, energy_reco=[1, 100] * u.TeV)
    assert_allclose(res.value, [0, 3])
    assert res.shape == (2,)


def test_background_2d_read_write(tmpdir, bkg_2d):
    filename = str(tmpdir / "bkg2d.fits")
    bkg_2d.to_fits().writeto(filename)

    bkg_2d_2 = Background2D.read(filename)

    axis = bkg_2d_2.data.axis('energy')
    assert axis.nbins == 2
    assert axis.unit == 'TeV'

    axis = bkg_2d_2.data.axis('offset')
    assert axis.nbins == 3
    assert axis.unit == 'deg'

    data = bkg_2d_2.data.data
    assert data.shape == (2, 3)
    assert data.unit == 's-1 MeV-1 sr-1'
