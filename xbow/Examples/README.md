Getting and Installing **AWS**
===============================

This configures AWS on your machine. For this workshop we have provided you with trial accounts which you should have received by email.

    pip install awscli

Then run

    aws configure

Which will prompt you for your credentials provided.


Getting and Installing **Xbow**
===============================

The recommended method to install **Xbow** is using pip

    pip install xbow
    
Then configure Xbow using

    xbow-config
    
Finally for this workshop we will need a filesystem

    xbow-create_filesystem

Using **Xbow-Launch**
===============================

**xbow-launch** boots a xbow head node ready to receive jobs. Booting is easy

    xbow-launch
    
    
