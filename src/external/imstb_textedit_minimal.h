#pragma once

////////////////////////////////////////////////////////////////////////
//
//     STB_TexteditState
//
// Definition of STB_TexteditState which you should store
// per-textfield; it includes cursor position, selection state,
// and undo state.
//

#ifndef IMSTB_TEXTEDIT_UNDOSTATECOUNT
#define IMSTB_TEXTEDIT_UNDOSTATECOUNT   99
#endif
#ifndef IMSTB_TEXTEDIT_UNDOCHARCOUNT
#define IMSTB_TEXTEDIT_UNDOCHARCOUNT   999
#endif
#ifndef IMSTB_TEXTEDIT_CHARTYPE
typedef int IMSTB_TEXTEDIT_CHARTYPE;
#endif
#ifndef IMSTB_TEXTEDIT_POSITIONTYPE
typedef int IMSTB_TEXTEDIT_POSITIONTYPE;
#endif

struct StbUndoRecord
{
   // private data
   IMSTB_TEXTEDIT_POSITIONTYPE  where;
   IMSTB_TEXTEDIT_POSITIONTYPE  insert_length;
   IMSTB_TEXTEDIT_POSITIONTYPE  delete_length;
   int                        char_storage;
};

struct StbUndoState
{
   // private data
   StbUndoRecord          undo_rec [IMSTB_TEXTEDIT_UNDOSTATECOUNT];
   IMSTB_TEXTEDIT_CHARTYPE  undo_char[IMSTB_TEXTEDIT_UNDOCHARCOUNT];
   short undo_point, redo_point;
   int undo_char_point, redo_char_point;
};

struct STB_TexteditState
{
   /////////////////////
   //
   // public data
   //

   int cursor;
   // position of the text cursor within the string

   int select_start;          // selection start point
   int select_end;
   // selection start and end point in characters; if equal, no selection.
   // note that start may be less than or greater than end (e.g. when
   // dragging the mouse, start is where the initial click was, and you
   // can drag in either direction)

   unsigned char insert_mode;
   // each textfield keeps its own insert mode state. to keep an app-wide
   // insert mode, copy this value in/out of the app state

   int row_count_per_page;
   // page size in number of row.
   // this value MUST be set to >0 for pageup or pagedown in multilines documents.

   /////////////////////
   //
   // private data
   //
   unsigned char cursor_at_end_of_line; // not implemented yet
   unsigned char initialized;
   unsigned char has_preferred_x;
   unsigned char single_line;
   unsigned char padding1, padding2, padding3;
   float preferred_x; // this determines where the cursor up/down tries to seek to along x
   StbUndoState undostate;
};