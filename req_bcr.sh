[ -d bar_chart_race ] && { pushd bar_chart_race; git pull; popd; } || git clone --depth=1 --single-branch https://github.com/dexplo/bar_chart_race bar_chart_race
cd bar_chart_race
pip install .
