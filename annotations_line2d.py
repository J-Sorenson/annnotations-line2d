# -*- coding: utf-8 -*-
"""
annotations_line2d module
Created on Thu Sep 10 21:51:23 2015
@author: James Sorenson
"""

import matplotlib
import matplotlib.pyplot as plt
# This is to prevent overlapping annotations from being dragged simultaneously
# due to the multi-threaded nature of the matplotlib gui.
import threading
###########################
# Globals
###########################
attr_name = 'annotations_line2d'

_event= None # Used for debugging


###########################
# Class definitions
###########################
class DraggableAnnotationLine2D(matplotlib.offsetbox.DraggableBase):
    """This class is like Matplotlib’s DraggableAnnotation, but this one actually works.
    Apparently, the original class can't handle annotations that are created
    using 'offset points' from a data point. This class ONLY works with those.
    Left-click to move the annotation without changing the data point.
    Middle-click to slide the annotation to a different data point.
    Right-click to delete the annotation.
    The original annotation artist is in self.ref_artist.
    We save additional info in self.line, self.index, and self.formatter.
    """
    # Class-level lock to make sure only ONE annotation is moved at a time.
    # Due to QT's multi—threaded nature, it‘s best to use a real thread lock.
    _drag_lock=threading.Lock()
    _counter=0 # Just a counter to give each annotation a unique ID.
    
    def __init__(self, ref_artist, line=None, index=None, formatter=None, use_blit=True):
        # Use the base init (This isn‘t C++ where the parent is called automatically.)
        super().__init__(ref_artist, use_blit=use_blit)
        # Store the other parameters
        self.line=line
        self.index=index
        self.formatter=formatter
        # Create a unique ID for this annotation (for debugging)
        DraggableAnnotationLine2D._counter += 1
        DraggableAnnotationLine2D._counter %= 2**31 # Not too big
        self.id = DraggableAnnotationLine2D._counter
        #print('Init',self.id)
        if formatter is not None:
            # Get and set the text
            self.ref_artist.set_text(self.formatter(line, index))
        #Update the canvas to make sure the annotation is visible
        self.canvas.draw()
    
    
    def artist_picker(self, artist, event):
        """
        Determines if the artist should enable move for this mouse button event
        """
        # Make sure this only happens with a click. Ignore scroll.
        # Left or Right click works on all of these annotations
        # Middle click (slide) requires that line and index are assigned
        if (event.button in (1,3)) or \
            (event.button ==2 and self.line is not None and self.index is not None):
            # Good action. We only want to drag if the cursor is inside the
            # box, not the arrow and the area around it.
            # contains(event) returns (bool,attr)
            #print('Picked',self.id)
            drag = self.ref_artist.get_bbox_patch().contains(event)
            if drag[0]:
                #Make sure no other annotation are dragging.
                # wait=False means no block. True if a successful lock.
                if DraggableAnnotationLine2D._drag_lock.acquire(False):
                    # Record the mouse button
                    self.button=event.button
                    #print('Claim',self.id)
                    return drag
        # If we made it here, then we're not moving
        return (False, None)


    def save_offset(self):
        """
        On button-down, this saves the current location of the annotation.
        Annotation object is in self.ref_artist.
        """
        #print('Save',self.id)
        if self.button == 1:
            # Left-click. Move the annotation while pointing at the same data.
            # Get the starting position of the artist in points (relative to data point)
            self.drag_start_text_points = self.ref_artist.get_position()
            # Get the inverted transform so we can convert pixels to paints.
            self.drag_trans_mat = self.ref_artist.get_transform().inverted().get_matrix()
        elif self.button == 2:
            # Middle-click. We need some additional information to slide the data.
            self.xydata=self.line.get_xydata() #just makes it easier (this does NOT copy)
            # we need the pixels of the starting data point (not the cursor)
            self.drag_start_pixels = self.ref_artist.get_axes().transData.transform(self.ref_artist.xy)
            # Get the translation from pixels to data for annotation.xy
            self.drag_trans_pix2dat = self.ref_artist.get_axes().transData.inverted()
            

    def update_offset(self, dx, dy):
        """
        dx and dy is the total pixel offset from the point where the mouse
        drag started.
        """
        if self.button == 1: # Left—click
            # Scale delta pixels to delta points using parts of annotation transform.
            # The full transform includes the data offset, but set position already does that.
            new_position=(self.drag_start_text_points[0] + dx * self.drag_trans_mat[0,0],
                          self.drag_start_text_points[1] + dy * self.drag_trans_mat[1,1])
            # Apply as delta points from data point
            self.ref_artist.set_position(new_position)
        elif self.button == 2: # Middle—click
            # We may have a logarithmic scale, but update offset only gives us delta pixels.
            # Add the delta to the starting pixels, then convert to data coordinates
            pixels_dxy = matplotlib.numpy.array((dx,dy))
            new_data_xy = self.drag_trans_pix2dat.transform(self.drag_start_pixels+pixels_dxy)
            # Determine if the new data coordinates reach or exceed the next line data point.
            index=self.index
            while (index > 0) and (self.xydata[index-1][0] > new_data_xy[0]):
                #Move left
                index -= 1
            while (index < self.xydata.shape[0] - 1) and (self.xydata[index+1][0] < new_data_xy[0]):
                # Move right
                index += 1
            if index != self.index:
                # we moved an index! Update the annotation
                self.ref_artist.xy=self.xydata[index,:]
                self.index=index
                if self.formatter is not None:
                    # Update the text in the annotation
                    self.ref_artist.set_text(self.formatter(self.line, index))
 
           
    def finalize_offset(self):
        """Called when the mouse button is released, if this was picked in the first place."""
        #print('Finalize',self.id)
        if self.button == 2 and self.formatter is not None:
            # Print out annotation text for the user to copy/paste
            self.print_annotation()
        elif self.button == 3:
            # Delete annotation
            self.remove()
        
    
    def on_release(self,event):
        """
        Called when the mouse button is released, whether or not this was picked.
        We extend this function so that we are guaranteed to release the thread lock.
        """
        # Call the original
        super().on_release(event)
        #Everyone tries to remove the block, just in case the controlling annotation was removed.
        try:
            DraggableAnnotationLine2D._drag_lock.release()
        except RuntimeError:
            pass # Already released. Not a concern.
        
        
    def print_annotation(self):
        """Does exactly what you think it does"""
        print('Annotation: {0}, ind={1}\n{2}'.format(self.line.get_label(), self.index, self.ref_artist.get_text()))


    def remove(self):
        """Disconnect and delete the annotation."""
        #print('Remove',self.id)
        self.disconnect() # Disconnect the callbacks
        self.ref_artist.remove() # Delete the annotation artist
        self.got_artist=False # Tell this class it no longer has an artist
        self.canvas.draw() # Update the whole canvas so the annotation disappears
        
        
class AnnotationPicker(object):
    """
    A class to enable convenient annotations to any plot.
    This is meant only for 2D lines.
    Left-click to move the annotation without changing the data point.
    Middle-click to slide the annotation to a different data point.
    Right-click to delete the annotation.
    Optional arguments:
        artists: (default None) A single or list of artists to attach this to as 'artist annotations'
        tolerance : (default 5) Picker tolerance to a line's data point to create an annotation.
        formatter : function to generate the string in the annotation. fcn(Line2D artist, index)
        All other keyword arguments Will be passed to the annotation.
    """
    
    def __init__(self, artists=None, tolerance=5, formatter=None, button=1, key = 'control', use_blit=True, **kwargs):
        # Parse the arguments
        self.tolerance = tolerance
        self.use_blit = use_blit
        self.button = button
        self.key=key
        if formatter is None: # Use default
            self.formatter=self._annotate_line_str
        else:
            self.formatter = formatter
        # Save the annotation parameters
        self.annotation_kwargs = dict(xycoords='data', textcoords='offset points',
            fontsize=11, picker=True, xytext=(20, 20),
            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
            arrowprops=dict(shrink=0.05, headwidth=5, width=1))
        # Add in additional/modified user parameters
        self.annotation_kwargs.update(kwargs)
        # Apply this annotation instance to the given artists and children
        if artists is not None:
            self.apply(artists)
        
        
    def apply(self, artists):
        """
        Enable picker on lines so that annotations are activated.
        This particular Annotation instance will be applied to this artist and
        its children (unless the children already have their own instance.
        Use 'clear annotaions' if you wish to override children settings.
        """
        # This is overly complex, but it allows the user to throw anything at it (figure, axes, line, etc)
        # Make it iterable for convenience
        artists = _make_iterable(artists)
        for artist in artists:
            if artist is None:
                continue
            # Attach this instance to the given artists
            setattr(artist, attr_name, self)
            # Enable picker to any line contained in this artist that is not already enabled.
            if isinstance(artist, matplotlib.lines.Line2D) and not artist.pickable():
                lines = [artist]
            elif isinstance(artist, matplotlib.axes.Axes):
                lines = [line for line in artist.get_lines() if not line.pickable()]
            elif isinstance(artist, matplotlib.figure.Figure):
                lines = [line for ax in artist.get_axes() for line in ax.get_lines() if not line.pickable()]
            else:
                lines=[]
            for line in lines:
                line.set_picker(self.tolerance)
                
        # Make sure the callbacks are enabled for the parent canvas
        enable_callbacks(artist)
        
        
    def annotate(self, line, index, text=None):
        """
        Makes a draggable, interactive annotation on the given line,
        at the given index, with the given text.
        line : Line2D object to annotate
        index : The index of the line to put the annotation
        text : The text to fill the annotation with. If None, then use default.
        Returns a DraggableAnnotationLine2D instance where the annotation artist is in self.ref_artist.
        """        
        if text is None:
            # Get the text from the formatter
            formatter=self.formatter
        else:
            # Manual text is given. Don't use the formatter
            formatter = None
        # Create the annotation at the designated point
        ax=line.get_axes()
        annot=ax.annotate(text, line.get_xydata()[index,:], **self.annotation_kwargs)
        # Make it draggable using our class, then return the object
        return DraggableAnnotationLine2D(annot, line, index, formatter, use_blit=self.use_blit)
        
        
    def _annotate_line_str(self, line, index):
        """
        The default function to take a Line2D artist and index and generate a
        string for the annotation box.
        """
        xy=line.get_xydata()[index]
        return '{0}[{1}]:\nx={2:.9}\ny:{3:.9}'.format(line.get_label(),index,xy[0],xy[1])
        
        
    def _onpick(self,event):
        """Called by canvas pick event."""
        if event.mouseevent.button == self.button and \
            event.mouseevent.key == self.key and \
            isinstance(event.artist, matplotlib.lines.Line2D):
            # More than one index may be in range. Determine the middle index.
            ind = event.ind[len(event.ind)//2]
            global _event
            _event=event
            # Generate the annotation
            self.annotate(event.artist, ind)
        
        
###########################
# Module functions
###########################

def enable_callbacks(artist):
    """
    Enable annotation callbacks within this canvas/figure.
    This adds the .annotations attribute to the canvas to hold the callbacks.
    """
    if isinstance(artist, matplotlib.figure.Figure):
        canvas=artist.canvas
    elif hasattr(artist, 'get_figure'):
        canvas=artist.get_figure().canvas
    else:
        canvas=artist
        
    if not hasattr(canvas,attr_name):
        # Add the callbacks and store as a list in the canvas attribute
        callbacks=[]
        callbacks.append(canvas.mpl_connect('pick_event', _on_pick_event))
        callbacks.append(canvas.mpl_connect('figure_enter_event', _on_figure_enter_event))
        setattr(canvas, attr_name, callbacks)


def disable_callbacks(canvas):
    """
    Disable all annotation callbacks pertaining to this callback.
    We leave the pickers and annotation instances in the artists.
    We just get rid of the callback attached to the canvas.
    """
    if isinstance(canvas, matplotlib.figure.Figure):
        canvas=canvas.canvas # We were given the figure instead
    for callback in getattr(canvas, attr_name, []):
        canvas.mpl_disconnect(callback)
    delattr(canvas, attr_name)
    print('AnnotationPicker callback removed from canvas.')


def annotate(line, index, text=None):
    """
    Wrapper function around AnnotationPicker.annotate()
    This will find the controlling instance of Annotations for the given line
    and create an interactive annotation at the given index with the given text.
    Input:
        line: The matplotlib line object to annotate (plt.figure(1).axes[0].lines[0])
        index: The index of the line to annotate.
        text: The annotation text. It None, then the AnnotationPicker.formatter()
            is used to generate text at the given line and index.
    Returns:
        DraggableAnnotationLine2D object
    """
    annotations_instance = _find_annotations_instance(line)
    if annotations_instance is None:
        # Create a default annotation for this line
        annotations_instance = AnnotationPicker(line)
        setattr(line, attr_name, annotations_instance)
    annotations_instance.annotate(line, index, text)


def subplots(*args, anno=None, **kwargs):
    """
    Identical to plt.subplots(), but  also assigns an AnnotationPicker class
    to the figure.  Use "anno=AnnotationPickerInstance" to use a specific instance
    of the AnnotationPicker.
    """
    # Since we are using plt.subplots, this will show immediately if interactive.
    # gca and gcf will also be updated.
    fig,ax_list=plt.subplots(*args, **kwargs)
    if anno is None:
        # Create default AnnotationPicker that will be connected to the figure
        AnnotationPicker(fig)
    else:
        anno.apply(fig)
    return (fig,ax_list)


###########################
# Private Utilites
###########################

def _make_iterable(obj):
    """Return obj as a list if it is not already an iterable object"""
    if hasattr(obj,'__iter__'):
        return obj
    else:
        # Make it iterable for consistency
        return [obj]


def _find_annotations_instance(artist):
    """
    Find the controlling Annotations instance for this artists.
    It could be attached to the artist itself, or on the parent axes or figure.
    Returns the controlling Annotations instance.
    """
    if hasattr(artist, attr_name):
        # Instance is attached to the artist itself
        return getattr(artist, attr_name)
    elif hasattr(artist, 'get_axes' ) and hasattr(artist.get_axes(), attr_name):
        # Instance is attached to the axes
        return getattr(artist.get_axes(), attr_name)
    elif hasattr(artist, 'get_figure') and hasattr(artist.get_figure(), attr_name):
        # Instance is attached to the figure
        return getattr(artist.get_figure(), attr_name)
        # No instance found
    return None
    
def _clear_annotations(artist):
    """
    Call this on any artist to clear the annotation instances for that artist
    and all of its children. Mostly useful for debugging.
    """
    artists = _make_iterable(artist)
    for artist in artists:
        if hasattr(artist, attr_name):
            delattr(artist, attr_name)
            if hasattr(artist,'get chlldren'):
                _clear_annotations(artist.get_children())
    print('All annotations in artist and children deleted.')
    
    
###########################
# Canvas Callback functions
###########################
def _on_pick_event(event):
    """
    This is what initially gets called when ANY artist in the figure with
    picking enabled is picked.
    Startlng with the artist itself, thls function will determine the closest
    AnnotationPicker instance to call. This permits different settings per
    line or per axes.
    """
    annotations_instance = _find_annotations_instance(event.artist)
    if annotations_instance is not None:
        # Call the controlling Annotations instance
        annotations_instance._onpick(event)


def _on_figure_enter_event(event):
    """
    When the mouse enters the figure, this will make sure all lines have
    picker enabled so that new lines can be annotated.
    """
    fig=event.canvas.figure
    # Only lines that are not already pickable will be updated.
    lines=[line for ax in fig.axes for line in ax.lines if not line.pickable()]
    for line in lines:
        # The controlling Annotations instance is either in the axes or figure.
        annotations_instance=_find_annotations_instance(line)
        if annotations_instance is not None:
            line.set_picker(annotations_instance.tolerance)
    # We may need to update legends if the user manually plotted or deleted a line.
    #legend_update(fig, draw=True) #Draw if a change was detected
    
    
###########################
# TEST
###########################
if __name__ == '__main__':
    import numpy as np
    plt.ion()
    # Use our subplots wrapper to make sure annotations are enabled
    fig,ax=subplots(2,1)
    ax[0].set_title('click on points')
    x=np.r_[-5:5:.1]
    y=x**2-5*x+3
    lines=[]
    lines += ax[0].plot(x,x**2-5*x+3, '-.',label='My Line')
    lines += ax[1].plot(x,5*x+4,label='Line2')
    # Enable Annotations
    anno=AnnotationPicker(fig)
    an=anno.annotate(ax[0].lines[0],30, 'A manual annotation')
    # Add a legend
    #leg=legend(ax)
    # Add another line and see if moving the mouse in catches it
    ax[1].plot(x,2*x+7, label='New line')
    # Create custom string for 2nd axes
    def custom_text(line,ind):
        xy=line.get_xydata()[ind]
        custom='Custom text\nData[{0}]: {1:.9}, {2:.9}'.format(ind,xy[0],xy[1])
        return custom
    
    anno2=AnnotationPicker(ax[1],formatter=custom_text, key=None)
    ax[1].plot(x,y, '.-',label='No picker yet') # See if the picker gets enabled
    ax[1].legend()
    plt.draw()
