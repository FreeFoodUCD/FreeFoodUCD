-- Fix UCD Computer Science Society Instagram handle
UPDATE societies 
SET instagram_handle = 'ucdnetsoc', 
    name = 'UCD Netsoc (Computer Science Society)'
WHERE instagram_handle = 'ucdcompsci';
