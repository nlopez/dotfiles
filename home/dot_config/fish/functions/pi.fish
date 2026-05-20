function pi --wraps pi --description 'Run pi with AWS_PROFILE unset'
    set --erase AWS_PROFILE
    command pi $argv
end
