# Set this to true to allow using the builtin source command to source Python files as
# well as regular shell scripts. This is pretty cool so I'd recommend turning it on!
: ${SOURCEPY_OVERLOAD_SOURCE:=true}

# Allow this tool to auto update itself from the github repo. Whilst this option is here
# if you want it, the securityconscious should consider whether they really want to allow
# strangers to run arbitrary code without on their systems without vetting it first.
: ${SOURCEPY_AUTO_UPDATE:=false} # todo - does nothing right now



SOURCEPY_BIN="$(dirname $0)/src"

sourcepy() {
    local python_bin=${PYTHON_BIN:-$(which python3)}
    local module_stub=$($python_bin ${SOURCEPY_BIN}/source.py $1)
    builtin source $module_stub
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


