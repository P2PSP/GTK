def update_widget(BUFFER_STATUS):
    Buffering_Adapter.WIDGET.set_fraction(float(BUFFER_STATUS)/100)
    
    
class Buffering_Adapter():
    
    WIDGET = None
    
    def set_widget(self,progress_bar):
       Buffering_Adapter.WIDGET = progress_bar
