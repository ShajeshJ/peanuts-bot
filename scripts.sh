asdf_tool_version() {
    if [ $# -eq 0 ]; then
        echo "Missing tool name argument"
        return 1
    elif [ $# -gt 1 ]; then
        echo "Too many arguments: $@"
        return 1
    fi

    toolname="$1"

    version=$(cat .tool-versions | grep -w "$toolname" | cut -d ' ' -f2)

    if [ -z "$version" ]; then
        echo "could not detect required '$toolname' version"
        return 1
    fi

    echo "$version"
}

check_python() {
    required=$(asdf_tool_version python)
    if [ $? -ne 0 ]; then echo "$required"; return 1; fi

    py_output=$(python3 --version)
    if [ $? -ne 0 ]; then return 1; fi

    installed=$(echo "$py_output" | cut -d ' ' -f2)

    if [ "$required" != "$installed" ]; then
        echo "required python version $required does not match installed version $installed"
        return 1
    fi
}

install_poetry() {
    check_python
    if [ $? -ne 0 ]; then return 1; fi

    poetry_version="$(asdf_tool_version poetry)"
    if [ $? -ne 0 ]; then echo "$poetry_version"; return 1; fi

    echo "installing poetry==$poetry_version"
    python3 -m pip install "poetry==$poetry_version"
}

build_deploy() {
    install_poetry
    poetry install --only=main
}
