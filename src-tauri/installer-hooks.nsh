; Adds "Open in ManimPro" to File Explorer's right-click menu for folders
; (on a folder, and on the empty space inside one). Per-user, so no admin rights.

!macro NSIS_HOOK_POSTINSTALL
  WriteRegStr HKCU "Software\Classes\Directory\shell\ManimPro" "" "Open in ManimPro"
  WriteRegStr HKCU "Software\Classes\Directory\shell\ManimPro" "Icon" "$INSTDIR\${MAINBINARYNAME}.exe"
  WriteRegStr HKCU "Software\Classes\Directory\shell\ManimPro\command" "" '"$INSTDIR\${MAINBINARYNAME}.exe" "%1"'
  WriteRegStr HKCU "Software\Classes\Directory\Background\shell\ManimPro" "" "Open in ManimPro"
  WriteRegStr HKCU "Software\Classes\Directory\Background\shell\ManimPro" "Icon" "$INSTDIR\${MAINBINARYNAME}.exe"
  WriteRegStr HKCU "Software\Classes\Directory\Background\shell\ManimPro\command" "" '"$INSTDIR\${MAINBINARYNAME}.exe" "%V"'
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  DeleteRegKey HKCU "Software\Classes\Directory\shell\ManimPro"
  DeleteRegKey HKCU "Software\Classes\Directory\Background\shell\ManimPro"
!macroend
