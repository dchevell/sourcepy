sourcepy() {

    local sourcepy_home=${SOURCEPY_HOME:-"${HOME}/.sourcepy"}
    local python_bin=${PYTHON_BIN:-$(which python3)}
    local module_stub=$($python_bin ${sourcepy_home}/bin/source.py $1)
    builtin source $module_stub
}

source() {
    for sourcefile in "$@"
    do
        local extension="${sourcefile##*.}"
        if [[ "$extension" == "py" ]]
        then
            sourcepy $sourcefile
        else
            builtin source $sourcefile
        fi
    done
}

alias .=source


