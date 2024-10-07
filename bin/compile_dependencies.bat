@echo off

for /F "tokens=1" %%i in ('git rev-parse --show-toplevel') do set toplevel=%%i

cd %toplevel%

REM we are echo'ing the Linux variant here, simply because we have more Linux users
set CUSTOM_COMPILE_COMMAND="./bin/compile_dependencies.sh"

REM Base deps
pip-compile^
    --no-emit-index-url^
    %*^
    requirements/base.in

REM Dependencies for ci
pip-compile^
    --no-emit-index-url^
    --output-file requirements/ci.txt^
    %*^
    requirements/base.txt^
    requirements/test-tools.in^
    requirements/ci.in

REM Dev depedencies
pip-compile^
    --no-emit-index-url^
    --output-file requirements/dev.txt^
    %*^
    requirements/base.txt^
    requirements/test-tools.in^
    requirements/dev.in
