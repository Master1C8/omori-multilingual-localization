// Oculix recognition adapter. No IDE/Jython global input initialization.
import org.sikuli.script.Finder;
import org.sikuli.script.Pattern;
import org.sikuli.script.Match;
import javax.imageio.ImageIO;
import java.io.*;
public final class OculixMatch {
 static void match(String[] args) throws Exception {
  Finder f=new Finder(ImageIO.read(new File(args[0])));
  try {
   f.find(new Pattern(ImageIO.read(new File(args[1]))).similar(Float.parseFloat(args[2])));
   if(f.hasNext()){Match m=f.next();System.out.println("OCULIX_RESULT {\"matched\":true,\"x\":"+m.x+",\"y\":"+m.y+",\"score\":"+m.getScore()+"}");}
   else System.out.println("OCULIX_RESULT {\"matched\":false}");
  }finally{f.destroy();System.out.flush();}
 }
 public static void main(String[] args) throws Exception {
  nu.pattern.OpenCV.loadLocally();
  if(args.length==1&&args[0].equals("--serve")){
   BufferedReader r=new BufferedReader(new InputStreamReader(System.in));String line;
   while((line=r.readLine())!=null){try{match(line.split("\t"));}catch(Exception e){System.out.println("OCULIX_RESULT {\"error\":true}");e.printStackTrace(System.err);System.out.flush();}}
  }else match(args);
 }
}
