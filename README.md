# annnotations-line2d
Interactive annotations for 2D Lines in Python Matplotlib. 

This Python module was initially inspired by the mpl_datacursor module, but that module had many issues with draggable annotations when used with 2D Lines, and had multiple bugs with Matplotlib 1.4.3 when used with QT.  Besides, there were some other line-specific features I desired.  In true Python form: if you want a feature, make it!  

This provides draggable, interactive annotations specifically for 2D lines.  Features:
  - Ctrl-left-click on a line's data point to create an interactive annotation at that point.
    - The Key and Mouse button can be configured.  Use Shift right-click if you want.
    - The format of the annotation is generated from the Line artist and index.  You can customize that as well.
    - Because, multiple points may be in range of the "pick," it will only annotate the middle point.
  - Once the annotation is created, the following function are available:
    - Left-click to drag the annotation to a new position.
    - Middle-click to slide the annotation to a new data point.  The annotation text will live-update as you move.
    - Right-click to remove the annotation.
  
I use a thread lock to prevent overlapping annotations from being moved or deleted simultaneously.  Only the top one will be selected.  I've also added a replacement "subplots" command that is just a wrapper to plt.subplots, but adds a default annotations callback.

The module consists of two classes: 
  - DraggableAnnotationLine2D: The annotation itself.
  - AnnotationPicker: This class is attached (Monkey Patched) to a Matplotlib artist and creates the annotations when a child Line2D artist is picked.

Two callbacks are created on the canvas:
  - On Pick Event:  When a Line2D is picked, the event will search for the nearest AnnotationPicker instance attached.  First it looks on the Line2D artist itself, then the parent axes, and finally the figure.  This provides the flexibility of creating different annotation labels per line or per axes.
  - On Mouse Enter Figure : When the mouse enters the figure, the module searches for new 2D Lines and enables the picker.  This allows you to plot new lines without having to re-apply the annotations module to them.

My testing shows that blit works reliably, so it is enabled by default, but you can turn it off if you wish.  I tried to make it as efficient as possible.  If you run the module as a script, you'll get a sample plot to see the featurs.  Let me know if you have any questions.

To be clear: this module is specific to 2D Lines.  If you need annotations for other objects, then I strongly suggest you look at mpl_datacursor.  My work does not really involve other kinds of plots.  Otherwise, suggestions are welcom!

- Jim

Not only can you ctrl-click to pick a line to create an annotation, but then you can 
