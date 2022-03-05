
SOURCEPY_HOME="${HOME}/.sourcepy"

: ${SOURCEPY_DEBUG:=false}



sourcepy() {

    # Nested functions
    # These are local only so we don't pollute parent script namespace

        PYTHON_BIN=$(which python3)

        _log() {
            $SOURCEPY_DEBUG || return
            echo >&2 "sourcepy :: $*"
        }

        _die() {
            echo >&2 "sourcepy: $*"
            return 1
        }

        escape() {
            echo $1 | sed 's@[/ .]@_@g'
        }

        hashfn() {
            local hashfn
            hashfn=$(which sha256sum) || hashfn=$(which sha1sum) || hashfn=$(which shasum)
            $hashfn <<< $1 | awk '{print $1}'
        }

        abspath() {
            if [[ $(command -v realpath) ]]; then
                realpath $1
            else
                echo "$(cd "$(dirname "$1")"; pwd -P)/$(basename "$1")"
            fi
        }

        get_hash() {
            local src_hash=$(hashfn $1)
            local git_hash=$(git --git-dir "${SOURCEPY_HOME}/.git" rev-parse --verify HEAD)
            local bin_hash=$($hashfn <<< $(which $PYTHON_BIN))
            local stub_hash="src:${src_hash}::git:${git_hash}::bin:${bin_hash}"
            echo $stub_hash
        }

        has_changed() {
            $SOURCEPY_DEBUG && return 0
            local module_src=$1
            local stub_home=$2
            if [[ ! -f "$stub_home/stub.sh" || ! -f "$stub_home/stub.hash" ]]; then
                _log "$0: stub files missing"
                return 0
            fi

            local current_hash=$(get_hash $module_src)
            local last_hash=$(< "$stub_home/stub.hash")
            if [[ $current_hash != $last_hash ]]; then
                _log "$0: stub hash out of date"
                return 0
            fi
            _log "$0: no changes found"
            return 1
        }

        generate_stubs() {
            local module_src=$1
            local stub_home=$2
            local module_hash=$(get_hash $module_src)
            _log "generating stubs for $module_src"
            mkdir -p $stub_home
            echo $module_hash > "${stub_home}/stub.hash"
            local module_stub
            module_stub=$($PYTHON_BIN ${SOURCEPY_HOME}/bin/source.py $module_src)
            if [[ $? -ne 0 ]]; then
                return 1
            fi
            echo $module_stub > "$stub_home/stub.sh"
        }

    ###########################################################
    ##                                                       ##
    ##  SourcePy - Source python scripts like shell scripts  ##
    ##                                                       ##
    ###########################################################

    local module_src=$(abspath $1)

    if [[ -z $module_src ]]; then
        _die "not enough arguments"
    fi

    if [[ -f $module_src ]]; then
        local stub_home="${SOURCEPY_HOME}/stubs/$(escape $module_src)"
        if $(has_changed $module_src $stub_home); then
            generate_stubs $module_src $stub_home
        fi
        source "$stub_home/stub.sh"
    else
        _die "no such file or directory: $module_src"
    fi

}

