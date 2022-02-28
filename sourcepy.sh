
SOURCEPY_HOME="${HOME}/.sourcepy"

: ${PYTHON_BIN:=$(which python3)}
: ${SOURCEPY_LOGS_ENABLED:=false}



sourcepy() {

    # Nested functions
    # These are local only so we don't pollute parent script namespace

        _log() {
            $SOURCEPY_LOGS_ENABLED || return
            echo >&2 "sourcepy :: $*"
        }

        _die() {
            echo >&2 "$sourcepy: $*"
            return 1
        }

        escape() {
            echo $1 | sed 's@[/ .]@_@g'
        }

        get_hash() {
            # generate a file hash to use as a stub cache key
            # try to use available hash algos; fall back on file last mod date
            local hashfn
            hashfn=$(which sha256sum) || hashfn=$(which sha1sum) || hashfn=$(which md5sum)
            if [[ -n $hashfn ]]; then
                echo $($hashfn $1) | awk '{print $1}'
            else
                date -r $1 '+%s'
            fi
        }

        has_changed() {
            local module_src=$1
            local stub_home=$2

            if [[ ! -f "$stub_home/stub.sh" || ! -f "$stub_home/stub.hash" ]]; then
                return 0
            fi

            local current_hash=$(get_hash $module_src)
            local last_hash=$(< "$stub_home/stub.hash")

            if [[ $current_hash != $last_hash ]]; then
                echo $current_hash > $stub_hash_path
                return 0
            fi
            return 1
        }

        generate_stubs() {
            local module_src=$1
            local stub_home=$2
            local module_hash=$(get_hash $module_src)
            _log "generating stubs for $module_src"
            echo $module_hash > "${stub_home}/stub.hash"
            python3 ${SOURCEPY_HOME}/bin/source.py $module_src > "$stub_home/stub.sh"
        }

    ###########################################################
    ##                                                       ##
    ##  SourcePy - Source python scripts like shell scripts  ##
    ##                                                       ##
    ###########################################################

    local module_src=$1

    if [[ -z $module_src ]]; then
        _log $0 $@
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

