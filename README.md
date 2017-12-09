# Environment
* Python 2.7

# Setup Environment

```shell
virtualenv -p /usr/bin/python2.7 --no-site-packages ENV27
source ENV27/bin/activate
pip install -r requirement.txt
```

**Maybe you will meet this warning**
```
In file included from patch/include/boost/python/detail/prefix.hpp:13:0,
                     from patch/include/boost/python/args.hpp:8,
                     from patch/include/boost/python.hpp:11,
                     from src/pyltp.cpp:15:
    patch/include/boost/python/detail/wrap_python.hpp:50:23: fatal error: pyconfig.h: No such file or directory
     # include <pyconfig.h>
```

Try this
` sudo apt-get install python-dev python3-dev `

# How to use
1. Correct the MODELDIR in config.py

2. Run the REST server
```
source ENV27/bin/activate
python main.py
```
**Port default 5000**