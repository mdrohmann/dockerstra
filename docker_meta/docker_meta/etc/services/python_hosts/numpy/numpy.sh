pip install cython

cd /tmp \
 && git clone --branch=v1.9.2 --depth=1 https://github.com/numpy/numpy \
 && cd numpy \
 && python setup.py install \
 && cd /tmp \
 && rm -rf numpy

cd /tmp \
 && git clone --branch=v0.15.1 --depth=1 https://github.com/scipy/scipy \
 && cd scipy \
 && python setup.py install \
 && cd /tmp \
 && rm -rf scipy

