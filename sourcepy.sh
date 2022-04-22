# Set this to true to allow using the builtin source command to source
# Python files as well as regular shell scripts. This is pretty cool so
# I'd recommend leaving it on!
: ${SOURCEPY_OVERLOAD_SOURCE:=true}

# Sourcepy should automatically the `src` directory where Sourcepy's run
# scripts are located. If this isn't working, e.g. for shells other than
# bash or zsh, you can manually set this value in your environment.
: ${SOURCEPY_BIN:="$(dirname ${BASH_SOURCE[0]:-${(%):-%x}})/src"}


sourcepy() {
    local python_bin=${PYTHON_BIN:-$(which python3)}
    local module_wrapper=$($python_bin ${SOURCEPY_BIN}/source.py $1)
    builtin source $module_wrapper
}

if $SOURCEPY_OVERLOAD_SOURCE
then
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
fi


