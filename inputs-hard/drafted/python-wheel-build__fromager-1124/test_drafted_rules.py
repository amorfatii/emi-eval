import datetime
import pathlib
from hypothesis import given, settings, strategies as st, HealthCheck
from packaging.requirements import Requirement
from fromager import candidate, context, packagesettings, resolver
from fromager.requirements_file import RequirementType
_BOOTSTRAP_TIME = datetime.datetime(2026, 3, 26, 0, 0, 0, tzinfo=datetime.UTC)
_COOLDOWN = candidate.Cooldown(min_age=datetime.timedelta(days=7), bootstrap_time=_BOOTSTRAP_TIME)
_NO_FIXTURE_CHECK = settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=30)

def _make_ctx(tmp_path: pathlib.Path, cooldown: candidate.Cooldown | None=_COOLDOWN) -> context.WorkContext:
    settings_dir = tmp_path / 'settings'
    settings_dir.mkdir(exist_ok=True)
    return context.WorkContext(active_settings=packagesettings.Settings.from_files(settings_file=tmp_path / 'settings.yaml', settings_dir=settings_dir, patches_dir=tmp_path / 'patches', variant='cpu', max_jobs=None), constraints_file=None, patches_dir=tmp_path / 'patches', sdists_repo=tmp_path / 'sdists-repo', wheels_repo=tmp_path / 'wheels-repo', work_dir=tmp_path / 'work-dir', cooldown=cooldown)

def _cooldown_for(tmp_path: pathlib.Path, req: str, req_type: RequirementType) -> candidate.Cooldown | None:
    ctx = _make_ctx(tmp_path)
    return resolver.resolve_package_cooldown(ctx, Requirement(req), req_type=req_type)

def test_top_level_exact_pin_bypasses_cooldown(tmp_path: pathlib.Path) -> None:
    """A top-level requirement pinned with exact == has no cooldown."""
    assert _cooldown_for(tmp_path, 'test-pkg==1.2.3', RequirementType.TOP_LEVEL) is None

def test_top_level_unpinned_keeps_cooldown(tmp_path: pathlib.Path) -> None:
    """A top-level requirement without a pin still enforces the cooldown."""
    assert _cooldown_for(tmp_path, 'test-pkg', RequirementType.TOP_LEVEL) is _COOLDOWN

def test_top_level_range_keeps_cooldown(tmp_path: pathlib.Path) -> None:
    """A top-level requirement with a range specifier still enforces the cooldown."""
    assert _cooldown_for(tmp_path, 'test-pkg>=1.0,<3', RequirementType.TOP_LEVEL) is _COOLDOWN

def test_top_level_wildcard_pin_keeps_cooldown(tmp_path: pathlib.Path) -> None:
    """A top-level == pin with a wildcard does not exempt from the cooldown."""
    assert _cooldown_for(tmp_path, 'test-pkg==1.2.*', RequirementType.TOP_LEVEL) is _COOLDOWN

def test_top_level_compatible_release_keeps_cooldown(tmp_path: pathlib.Path) -> None:
    """A top-level ~= specifier does not exempt from the cooldown."""
    assert _cooldown_for(tmp_path, 'test-pkg~=1.2.0', RequirementType.TOP_LEVEL) is _COOLDOWN

def test_top_level_not_equal_keeps_cooldown(tmp_path: pathlib.Path) -> None:
    """A top-level != specifier does not exempt from the cooldown."""
    assert _cooldown_for(tmp_path, 'test-pkg!=1.2.3', RequirementType.TOP_LEVEL) is _COOLDOWN

def test_install_dependency_exact_pin_keeps_cooldown(tmp_path: pathlib.Path) -> None:
    """An exact == pin on a transitive install dependency still enforces the cooldown."""
    assert _cooldown_for(tmp_path, 'test-pkg==1.2.3', RequirementType.INSTALL) is _COOLDOWN

def test_build_dependency_exact_pin_keeps_cooldown(tmp_path: pathlib.Path) -> None:
    """An exact == pin on a build dependency still enforces the cooldown."""
    for req_type in (RequirementType.BUILD_SYSTEM, RequirementType.BUILD_BACKEND, RequirementType.BUILD_SDIST):
        assert _cooldown_for(tmp_path, 'test-pkg==1.2.3', req_type) is _COOLDOWN

def test_same_package_exempt_top_level_but_enforced_transitive(tmp_path: pathlib.Path) -> None:
    """The same pinned package is exempt at top level but enforced as a transitive dependency."""
    ctx = _make_ctx(tmp_path)
    req = Requirement('test-pkg==1.2.3')
    top = resolver.resolve_package_cooldown(ctx, req, req_type=RequirementType.TOP_LEVEL)
    trans = resolver.resolve_package_cooldown(ctx, req, req_type=RequirementType.INSTALL)
    assert top is None
    assert trans is _COOLDOWN

def test_top_level_exact_pin_without_global_cooldown_has_none(tmp_path: pathlib.Path) -> None:
    """With no cooldown configured, a top-level exact pin resolves with no cooldown."""
    ctx = _make_ctx(tmp_path, cooldown=None)
    result = resolver.resolve_package_cooldown(ctx, Requirement('test-pkg==1.0'), req_type=RequirementType.TOP_LEVEL)
    assert result is None
_versions = st.from_regex('[0-9]{1,3}(\\.[0-9]{1,3}){0,3}', fullmatch=True)

@_NO_FIXTURE_CHECK
@given(version=_versions)
def test_any_top_level_exact_pin_is_exempt(tmp_path: pathlib.Path, version: str) -> None:
    """Every top-level requirement pinned with an exact == version is exempt from the cooldown."""
    assert _cooldown_for(tmp_path, f'test-pkg=={version}', RequirementType.TOP_LEVEL) is None

@_NO_FIXTURE_CHECK
@given(version=_versions, req_type=st.sampled_from([t for t in RequirementType if t != RequirementType.TOP_LEVEL]))
def test_any_non_top_level_exact_pin_enforces_cooldown(tmp_path: pathlib.Path, version: str, req_type: RequirementType) -> None:
    """No non-top-level requirement is exempt from the cooldown because of an == pin."""
    assert _cooldown_for(tmp_path, f'test-pkg=={version}', req_type) is _COOLDOWN

@_NO_FIXTURE_CHECK
@given(version=_versions)
def test_any_top_level_wildcard_pin_enforces_cooldown(tmp_path: pathlib.Path, version: str) -> None:
    """A top-level == pin ending in a wildcard never exempts the package from the cooldown."""
    assert _cooldown_for(tmp_path, f'test-pkg=={version}.*', RequirementType.TOP_LEVEL) is _COOLDOWN